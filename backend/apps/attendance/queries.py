"""Read-side queries and reference resolution for attendance."""

from django.db.models import Case, Exists, IntegerField, OuterRef, Q, Value, When
from django.db.models.functions import Concat

from apps.academics.models import AcademicCycle, Grade, Section, Shift
from apps.attendance.models import (
    AttendanceAlert,
    AttendanceEvent,
    AttendancePermit,
    CaptureBatch,
    ControlPoint,
    JornadaParameters,
    Justification,
    JustificationAttachment,
    JustificationReason,
    ManualRegistrationReason,
    StudentCredential,
)
from apps.common.exceptions import AuthorizationError, DomainError, ResourceNotFoundError
from apps.common.listing import descending_too, search_and_order
from apps.identity.scopes import authorized_student_queryset
from apps.students.models import Student


def jornada_parameters():
    return JornadaParameters.objects.select_related("shift", "academic_cycle").all()


def attendance_events(*, students, student_id=None):
    rows = AttendanceEvent.objects.filter(student__in=students)
    if student_id:
        rows = rows.filter(student__public_id=student_id)
    return rows.select_related(
        "student__person", "shift", "control_point", "manual_reason", "operator"
    ).order_by("-captured_at", "-pk")


def attendance_alerts(*, students):
    return AttendanceAlert.objects.filter(student__in=students).select_related(
        "student__person", "shift", "section"
    )


def control_points():
    # INC-011: orden estable para paginar; (campus, code) es unico e indexado.
    return ControlPoint.objects.select_related("campus").order_by("campus_id", "code")


def manual_registration_reasons(*, is_active=True):
    """
    RF-ASI-012: the form only offers reasons still in use. A retired reason
    (``is_active=False``) is rejected by ``record_attendance_event`` anyway,
    so listing it by default would only offer a choice that fails;
    ``is_active=False`` lists the retired ones for whoever audits the catalogue.
    """
    return ManualRegistrationReason.objects.filter(is_active=is_active).order_by("code")


def _payload_get(queryset, public_id, label):
    try:
        return queryset.get(public_id=public_id)
    except (queryset.model.DoesNotExist, ValueError, TypeError) as exc:
        raise DomainError(f"No se encontró {label}.") from exc


def student_for_payload(public_id):
    return _payload_get(Student.objects.all(), public_id, "el estudiante")


def shift_for_payload(public_id):
    return _payload_get(Shift.objects.all(), public_id, "la jornada")


def grade_for_payload(public_id):
    return _payload_get(Grade.objects.all(), public_id, "el grado")


def section_for_payload(public_id):
    return _payload_get(Section.objects.all(), public_id, "la seccion")


def academic_cycle_for_payload(public_id):
    return _payload_get(AcademicCycle.objects.all(), public_id, "el ciclo escolar")


def control_point_for_payload(public_id):
    return _payload_get(ControlPoint.objects.all(), public_id, "el punto de control")


def justification_for_payload(public_id):
    return _payload_get(Justification.objects.all(), public_id, "la justificacion")


def justification_reasons():
    return JustificationReason.objects.order_by("code")


def justification_reason_for_payload(public_id):
    return _payload_get(JustificationReason.objects.all(), public_id, "el motivo")


def attendance_permit_for_payload(public_id):
    return _payload_get(AttendancePermit.objects.all(), public_id, "el permiso")


def capture_batch_for_payload(public_id, *, operator):
    """
    RF-ASI-009: resolve a batch by public id, scoped to its own operator --
    a batch belonging to someone else does not exist as far as this caller
    is concerned, same vague-not-found rule ``_payload_get`` already applies
    to every other lookup here.
    """
    return _payload_get(
        CaptureBatch.objects.filter(operator=operator), public_id, "el lote de captura"
    )


def manual_reason_for_payload(public_id):
    return _payload_get(ManualRegistrationReason.objects.all(), public_id, "el motivo")


def student_by_code(student_code):
    return Student.objects.filter(student_code=student_code, is_active=True).first()


def scan_transmission(*, batch_id, item_count):
    return (
        AttendanceEvent.Transmission.BATCH
        if batch_id or item_count > 1
        else AttendanceEvent.Transmission.INDIVIDUAL
    )


def origin_permissions():
    return {
        AttendanceEvent.Origin.SCAN: "attendance_scan",
        AttendanceEvent.Origin.MANUAL: "attendance_record_manual",
        AttendanceEvent.Origin.DECLARED: "attendance_declared_close",
    }


def movement_type_permissions():
    return {
        AttendanceEvent.MovementType.ENTRY: "attendance_record_entry",
        AttendanceEvent.MovementType.EXIT: "attendance_record_exit",
    }


def no_event_error():
    return ResourceNotFoundError(
        "No se encontró movimiento de asistencia para los criterios indicados."
    )


# --------------------------------------------------------------------------- #
# #631 (AS3/AS4) — bandejas de justificaciones y permisos
# --------------------------------------------------------------------------- #

STUDENT_SEARCH_FIELDS = ("student__student_code", "student_full_name")
REQUEST_ORDERINGS = {
    "submitted_at": ("created_at",),
    "status": ("status",),
    "student": ("student__person__last_name", "student__person__first_name"),
}
JUSTIFICATION_ORDERINGS = descending_too({**REQUEST_ORDERINGS, "absence_date": ("absence_date",)})
PERMIT_ORDERINGS = descending_too({**REQUEST_ORDERINGS, "permit_date": ("permit_date",)})


def _reviewable_or_own(queryset, *, user, resolve_codename):
    """
    Who sees which request (justification or permit) in the review queue:

    - whoever holds ``resolve_codename`` sees every request about a student
      inside their effective scope for that same permission (the same rule
      ``can_access_student`` applies student by student);
    - everyone sees the requests they submitted themselves.

    A reviewer without any effective scope keeps only their own submissions:
    the permission alone never widens the list to the whole institution.
    """
    visible = Q(submitted_by=user)
    if user.has_atomic_permission(resolve_codename):
        try:
            students = authorized_student_queryset(user=user, codename=resolve_codename)
        except AuthorizationError:
            students = None
        if students is not None:
            visible |= Q(student__in=students)
    return queryset.filter(visible)


def _request_rows(
    queryset, *, status, student_id, date_field, date_from, date_to, search, ordering, orderings
):
    if status:
        queryset = queryset.filter(status=status)
    if student_id:
        queryset = queryset.filter(student__public_id=student_id)
    if date_from:
        queryset = queryset.filter(**{f"{date_field}__gte": date_from})
    if date_to:
        queryset = queryset.filter(**{f"{date_field}__lte": date_to})
    queryset = queryset.annotate(
        student_full_name=Concat(
            "student__person__first_name", Value(" "), "student__person__last_name"
        ),
        # Pending first: a review queue opens on what still needs a decision.
        pending_rank=Case(
            When(status="pending", then=Value(0)), default=Value(1), output_field=IntegerField()
        ),
    ).order_by("pending_rank", "-created_at", "-pk")
    return search_and_order(
        queryset,
        search=search,
        ordering=ordering,
        search_fields=STUDENT_SEARCH_FIELDS,
        orderings=orderings,
    )


def _justification_queryset():
    return Justification.objects.select_related(
        "student__person",
        "reason_catalog",
        "submitted_by__person",
        "resolved_by__person",
    ).annotate(
        attachment_exists=Exists(
            JustificationAttachment.objects.filter(justification=OuterRef("pk"))
        )
    )


def visible_justifications(
    *, user, status=None, student_id=None, date_from=None, date_to=None, search=None, ordering=None
):
    """#631 (AS3): the justification review queue, filtered and ordered."""
    return _request_rows(
        _reviewable_or_own(
            _justification_queryset(),
            user=user,
            resolve_codename="attendance_justification_resolve",
        ),
        status=status,
        student_id=student_id,
        date_field="absence_date",
        date_from=date_from,
        date_to=date_to,
        search=search,
        ordering=ordering,
        orderings=JUSTIFICATION_ORDERINGS,
    )


def visible_justification(*, user, public_id):
    try:
        return _reviewable_or_own(
            _justification_queryset(),
            user=user,
            resolve_codename="attendance_justification_resolve",
        ).get(public_id=public_id)
    except Justification.DoesNotExist as exc:
        raise ResourceNotFoundError("No se encontró la justificación.") from exc


def _permit_queryset():
    return AttendancePermit.objects.select_related(
        "student__person", "submitted_by__person", "resolved_by__person"
    )


def visible_attendance_permits(
    *,
    user,
    status=None,
    student_id=None,
    permit_type=None,
    date_from=None,
    date_to=None,
    search=None,
    ordering=None,
):
    """#631 (AS4): the permit review queue, filtered and ordered."""
    queryset = _reviewable_or_own(
        _permit_queryset(), user=user, resolve_codename="attendance_permit_resolve"
    )
    if permit_type:
        queryset = queryset.filter(permit_type=permit_type)
    return _request_rows(
        queryset,
        status=status,
        student_id=student_id,
        date_field="permit_date",
        date_from=date_from,
        date_to=date_to,
        search=search,
        ordering=ordering,
        orderings=PERMIT_ORDERINGS,
    )


def visible_attendance_permit(*, user, public_id):
    try:
        return _reviewable_or_own(
            _permit_queryset(), user=user, resolve_codename="attendance_permit_resolve"
        ).get(public_id=public_id)
    except AttendancePermit.DoesNotExist as exc:
        raise ResourceNotFoundError("No se encontró el permiso.") from exc


# --------------------------------------------------------------------------- #
# #631 (AS2) — estado de la credencial
# --------------------------------------------------------------------------- #


def credential_status(*, student):
    """
    #631 (AS2): the state of the student's latest credential, without its
    token. ``opaque_identifier`` is never part of it: the QR is shown once, in
    the issuance response (``StudentCredentialSerializer``); reprinting means
    revoking and issuing a new one (RF-CRE-003/004).

    ``revoked_at`` is the row's ``updated_at``: a revoked credential is never
    written again (``revoke_credential`` is the last write it gets), so its
    last update is the revocation.
    """
    credential = (
        StudentCredential.objects.filter(student=student, is_active=True)
        .order_by("-issued_at", "-pk")
        .first()
    )
    if credential is None:
        return {
            "student_id": student.public_id,
            "status": "none",
            "public_id": None,
            "issued_at": None,
            "revoked_at": None,
            "revocation_reason": None,
        }
    revoked = credential.status == StudentCredential.Status.REVOKED
    return {
        "student_id": student.public_id,
        "status": credential.status,
        "public_id": credential.public_id,
        "issued_at": credential.issued_at,
        "revoked_at": credential.updated_at if revoked else None,
        "revocation_reason": credential.revocation_reason if revoked else None,
    }
