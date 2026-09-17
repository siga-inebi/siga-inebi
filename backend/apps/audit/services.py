from collections.abc import Mapping

from apps.audit.middleware import get_audit_context
from apps.audit.models import AuditEvent
from apps.common.exceptions import DomainError

SENSITIVE_CONTEXT_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "private_key",
    "credential",
    "credentials",
    "cookie",
    "cookies",
}


def sanitize_context(value):
    if isinstance(value, Mapping):
        sanitized = {}
        for key, nested_value in value.items():
            if str(key).lower() in SENSITIVE_CONTEXT_KEYS:
                continue
            sanitized[key] = sanitize_context(nested_value)
        return sanitized
    if isinstance(value, list):
        return [sanitize_context(item) for item in value]
    return value


def record_event(
    *,
    actor,
    action,
    resource,
    resource_identifier="",
    context=None,
    ip_address=None,
    reason="",
    changes=None,
):
    """
    ``reason`` and ``changes`` are RF-BIT-002's "motivo declarado" and "valor
    anterior y el nuevo" -- optional, so every existing call keeps behaving
    exactly as before. Both land inside ``context`` (no new columns): that's
    already where every other unstructured fact about an event lives.
    """
    merged_context = {}
    merged_context.update(get_audit_context())
    if context:
        merged_context.update(context)
    if reason:
        merged_context["reason"] = reason
    if changes:
        merged_context["changes"] = changes

    return AuditEvent.objects.create(
        actor=actor,
        actor_label=getattr(actor, "username", "") if actor else "",
        action=action,
        resource=resource,
        resource_identifier=resource_identifier,
        ip_address=ip_address or merged_context.get("ip_address") or None,
        context=sanitize_context(merged_context),
    )


def list_audit_events(
    *,
    actor_id=None,
    resource=None,
    resource_identifier=None,
    action=None,
    date_from=None,
    date_to=None,
):
    """
    RF-BIT-006: the filterable read of the audit trail. Callers must already
    have verified the actor holds the audit-read permission before calling
    this -- it applies the filters, it does not authorize the read.

    ``resource_identifier`` is what RF-EMI-007 needs to answer "que se le
    emitio a este estudiante": ``_record_document_issue`` already stamps it
    with the student's pk on every ``documents.document.issued`` event.
    """
    queryset = AuditEvent.objects.all()
    if actor_id is not None:
        queryset = queryset.filter(actor_id=actor_id)
    if resource:
        queryset = queryset.filter(resource=resource)
    if resource_identifier:
        queryset = queryset.filter(resource_identifier=resource_identifier)
    if action:
        queryset = queryset.filter(action=action)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    return queryset


def record_audit_export(*, actor, date_from, date_to, count):
    """RF-BIT-006: exporting audit entries is itself an audited operation."""
    return record_event(
        actor=actor,
        action="audit.export.created",
        resource="AuditEvent",
        context={
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "count": count,
        },
    )


def declare_data_retention(*, actor, category, period_days, legal_basis, applies_to_minors=False):
    """
    RNF-LEG-001: records a retention period for a category of data, with its
    legal/institutional justification. Declarative only -- this does not
    enforce or schedule any purge; the institution's retention policy is not
    yet finalized, so automated deletion is out of scope until it is.
    """
    if period_days <= 0:
        raise DomainError("El plazo de retencion debe ser un numero de dias mayor a cero.")
    if not legal_basis:
        raise DomainError("Debe declararse un fundamento legal para el plazo de retencion.")

    return record_event(
        actor=actor,
        action="compliance.retention.declared",
        resource="DataRetentionDeclaration",
        resource_identifier=category,
        context={
            "category": category,
            "period_days": period_days,
            "legal_basis": legal_basis,
            "applies_to_minors": applies_to_minors,
        },
    )


def record_sensitive_read(*, actor, action, resource, resource_identifier, student):
    """
    Audits a read that reveals sensitive/confidential data about one
    identified student (RF-BIT-003). Only call this when the request
    unambiguously names a single student -- never for aggregate or
    unscoped queries, which must not appear in the audit trail
    (docs/requirements/openspec/auditoria-bitacora.md).
    """
    return record_event(
        actor=actor,
        action=action,
        resource=resource,
        resource_identifier=resource_identifier,
        context={"student_id": student.pk, "result": "success"},
    )


def get_result_trace(*, enrolment, subject, actor):
    """
    Full audit trace behind one subarea's final grade (RF-RES-009): the unit
    grades that produced it, every correction applied with reason and
    author, and the recovery grade when one exists.

    Two independent correction trails already exist in the codebase and both
    are surfaced here (the issue's own wording, "las correcciones
    aplicadas", is generic, not scoped to one mechanism):

    - ``stage="live"``: a unit grade corrected while the cycle was still
      open (RF-CAL-005, ``register_unit_grade`` overwriting an existing
      ``Grade``), read from its ``evaluation.grade_updated`` audit event's
      ``changes.value`` diff. No reason is collected for this path today
      (RF-CAL-005 does not require one), so ``reason`` is always ``None``
      here.
    - ``stage="post_freeze"``: a frozen result corrected via the exceptional
      academic-authorization gap after the cycle closed (RF-RES-007,
      ``correct_frozen_subject_result``), read from
      ``FrozenSubjectResult`` rows marked ``is_correction`` plus their
      ``academics.frozen_subject_result.corrected`` audit event.

    Cross-domain read: audit-compliance is documented in domain-map.md as
    transversal to every other domain, so importing ``apps.academics`` and
    ``apps.evaluation`` here needs no exception note (unlike the crossings
    RF-RES-006/007/008 had to document).

    This is itself an audited sensitive read (RF-BIT-003): it names one
    identified student, so calling it records that fact regardless of what
    it finds. Authorization (``audit.read``, respecting role and scope per
    the issue's own security note) is enforced by the caller (view layer),
    same convention as every other service in this codebase.
    """
    from apps.academics import queries as academics_queries
    from apps.evaluation.models import Grade, RecoveryGrade

    unit_grades_qs = list(
        Grade.objects.filter(enrolment=enrolment, subject=subject)
        .select_related("evaluation_unit")
        .order_by("evaluation_unit__number")
    )
    unit_grades = [
        {
            "unit_number": grade.evaluation_unit.number,
            "unit_name": grade.evaluation_unit.name,
            "value": grade.value,
        }
        for grade in unit_grades_qs
    ]

    corrections = []
    unit_by_grade_id = {str(grade.pk): grade for grade in unit_grades_qs}
    if unit_by_grade_id:
        live_events = AuditEvent.objects.filter(
            action="evaluation.grade_updated",
            resource="Grade",
            resource_identifier__in=list(unit_by_grade_id),
        )
        for event in live_events:
            value_change = (event.context.get("changes") or {}).get("value")
            if not value_change:
                continue
            grade = unit_by_grade_id[event.resource_identifier]
            corrections.append(
                {
                    "stage": "live",
                    "unit_number": grade.evaluation_unit.number,
                    "previous_value": value_change.get("before"),
                    "new_value": value_change.get("after"),
                    "reason": None,
                    "corrected_by": event.actor_label or None,
                    "corrected_at": event.created_at,
                }
            )

    frozen_history = academics_queries.frozen_subject_result_history(
        enrolment=enrolment, subject=subject
    )
    for row in frozen_history:
        if not row.is_correction:
            continue
        event = (
            AuditEvent.objects.filter(
                action="academics.frozen_subject_result.corrected",
                resource="FrozenSubjectResult",
                resource_identifier=str(row.pk),
            )
            .order_by("created_at")
            .first()
        )
        final_grade_change = (
            (event.context.get("changes") or {}).get("final_grade") if event else None
        ) or {}
        corrections.append(
            {
                "stage": "post_freeze",
                "unit_number": None,
                "previous_value": final_grade_change.get("before"),
                "new_value": row.final_grade,
                "reason": row.correction_reason,
                "corrected_by": event.actor_label if event else None,
                "corrected_at": row.created_at,
            }
        )
    corrections.sort(key=lambda item: item["corrected_at"])

    recovery = (
        RecoveryGrade.objects.filter(enrolment=enrolment, subject=subject, is_active=True)
        .order_by("-created_at")
        .first()
    )

    record_sensitive_read(
        actor=actor,
        action="audit.result_trace.viewed",
        resource="ResultTrace",
        resource_identifier=f"{enrolment.public_id}:{subject.public_id}",
        student=enrolment.student,
    )

    return {
        "enrolment_id": str(enrolment.public_id),
        "subject_id": str(subject.public_id),
        "unit_grades": unit_grades,
        "recovery_grade": recovery.value if recovery is not None else None,
        "corrections": corrections,
    }


def diff_fields(instance, **candidates):
    """
    Before/after map for ``record_event(changes=...)``. Same ``None`` means
    "not supplied" convention every domain's ``_changed``-style helper
    already uses -- call this *before* mutating ``instance``.
    """
    return {
        name: {"before": getattr(instance, name), "after": new_value}
        for name, new_value in candidates.items()
        if new_value is not None
    }
