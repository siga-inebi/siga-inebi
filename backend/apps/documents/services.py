"""
Domain services for the document templates catalogue (RF-PLA-001).

Every invariant lives here, never in views or serializers (AGENTS.md #8).

Uniqueness is delegated to the database constraint and translated back into a
``DomainError`` by ``unique_violation_as``. Reading first and writing afterwards
would leave a window for two concurrent requests to both pass the check.
"""

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Max

from apps.audit.services import record_event
from apps.common.db import unique_violation_as
from apps.common.models import DomainError
from apps.documents.field_catalog import FIELD_TAGS
from apps.documents.models import DocumentTemplate, DocumentTemplateVersion
from apps.enrolments.services import pending_required_document_codes

SENSITIVE_FIELD_TAGS_PERMISSION = "student_view_sensitive"
OFFICIAL_ISSUANCE_PERMISSION = "document_issue"


def list_field_tags(*, actor=None, include_sensitive=False):
    """
    Fixed, predefined catalogue of dynamic tags templates may reference
    (RF-PLA-002). Sensitive/confidential tags are excluded by default
    (RF-PLA-003); including them requires ``student.view_sensitive``.
    """
    if not include_sensitive:
        return tuple(tag for tag in FIELD_TAGS if not tag[2])

    is_authorized = bool(
        actor
        and (actor.is_superuser or actor.has_atomic_permission(SENSITIVE_FIELD_TAGS_PERMISSION))
    )
    if not is_authorized:
        record_event(
            actor=actor,
            action="documents.field_tag_catalog.sensitive_read_denied",
            resource="FieldTag",
            context={"result": "denied", "reason": "missing_permission"},
        )
        raise PermissionDenied("Actor lacks permission to view sensitive field tags.")

    record_event(
        actor=actor,
        action="documents.field_tag_catalog.sensitive_read",
        resource="FieldTag",
        context={"result": "success"},
    )
    return FIELD_TAGS


def _clean_code(value, *, field="code"):
    code = (value or "").strip().upper()
    if not code:
        raise DomainError(f"A non-empty {field} is required.")
    return code


def _clean_name(value, *, field="name"):
    name = (value or "").strip()
    if not name:
        raise DomainError(f"A non-empty {field} is required.")
    return name


def _audit(actor, action, instance, **context):
    record_event(
        actor=actor,
        action=action,
        resource=type(instance).__name__,
        resource_identifier=str(instance.pk),
        context=context,
    )


def _changed(instance, actor, action, **candidates):
    """
    Apply the fields whose value was actually supplied, persist only those, and
    audit what changed. ``None`` means "not supplied", never "set to null".
    """
    fields = [name for name, value in candidates.items() if value is not None]
    for name in fields:
        setattr(instance, name, candidates[name])

    instance.save(update_fields=[*fields, "updated_at"])
    _audit(actor, action, instance, fields=fields)
    return instance


def _document_template_conflicts(code):
    return {
        "unique_document_template_code_per_institution": (
            f"Document template code '{code}' already exists for this institution."
        ),
    }


def _version_conflicts():
    return {
        "unique_document_template_version_sequence": ("Concurrent update detected; retry."),
    }


def _record_version(template):
    """Append an immutable content snapshot (RF-PLA-005)."""
    next_sequence = (template.versions.aggregate(Max("sequence"))["sequence__max"] or 0) + 1
    with unique_violation_as(_version_conflicts()):
        DocumentTemplateVersion.objects.create(
            template=template,
            sequence=next_sequence,
            name=template.name,
            kind=template.kind,
            description=template.description,
        )


@transaction.atomic
def create_document_template(
    *, institution, name, code, kind=DocumentTemplate.TemplateKind.OTHER, description="", actor=None
):
    """
    Register a document template.

    The code is normalised to upper case and unique per institution, including
    inactive templates, so history stays readable (same rule as campus codes,
    ADR-0006).
    """
    name = _clean_name(name)
    code = _clean_code(code)

    with unique_violation_as(_document_template_conflicts(code)):
        template = DocumentTemplate.objects.create(
            institution=institution,
            name=name,
            code=code,
            kind=kind,
            description=(description or "").strip(),
        )

    _audit(actor, "documents.template.created", template, code=code, kind=kind)
    _record_version(template)
    return template


@transaction.atomic
def update_document_template(*, template, name=None, description=None, kind=None, actor=None):
    """
    Update the descriptive attributes of a document template. The code is
    immutable. Any explicitly supplied field records a new version
    (RF-PLA-005); a call with nothing to change does not.
    """
    if name is not None:
        name = _clean_name(name)
    if description is not None:
        description = description.strip()

    updated = _changed(
        template,
        actor,
        "documents.template.updated",
        name=name,
        description=description,
        kind=kind,
    )

    if any(value is not None for value in (name, description, kind)):
        _record_version(updated)

    return updated


@transaction.atomic
def deactivate_document_template(*, template, actor=None):
    """Deactivate a document template instead of deleting it. Idempotent."""
    if not template.is_active:
        return template

    template.is_active = False
    template.save(update_fields=["is_active", "updated_at"])
    _audit(actor, "documents.template.deactivated", template)
    return template


def ensure_official_document_issuance_permission(*, actor):
    """
    Authorization gate for the official document issuance decision (RF-MAT-006).
    Denied attempts are audited, like the sensitive field tag catalogue.
    """
    is_authorized = bool(
        actor and (actor.is_superuser or actor.has_atomic_permission(OFFICIAL_ISSUANCE_PERMISSION))
    )
    if not is_authorized:
        record_event(
            actor=actor,
            action="documents.official_issuance.denied",
            resource="OfficialDocumentIssuance",
            context={"result": "denied", "reason": "missing_permission"},
        )
        raise PermissionDenied("Actor lacks permission to issue official documents.")

    return True


def evaluate_official_document_issuance(*, enrolment, actor=None):
    """
    Codes of the required documents that block official issuance (RF-MAT-006);
    an empty list means the enrolment is eligible. The decision is audited
    either way. Authorization is a separate concern, see
    ``ensure_official_document_issuance_permission``.
    """
    blocking_codes = pending_required_document_codes(enrolment=enrolment)
    if blocking_codes:
        _audit(
            actor,
            "documents.official_issuance.blocked",
            enrolment,
            pending_document_codes=blocking_codes,
        )
    else:
        _audit(actor, "documents.official_issuance.allowed", enrolment)

    return blocking_codes


def ensure_official_document_issuance_allowed(*, enrolment, actor=None):
    """Guard for issuance callers: raise when the enrolment is not eligible."""
    blocking_codes = evaluate_official_document_issuance(enrolment=enrolment, actor=actor)
    if blocking_codes:
        raise DomainError(
            "Official document issuance is blocked by pending required documents: "
            f"{', '.join(blocking_codes)}."
        )

    return True
