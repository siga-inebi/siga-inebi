"""
Domain services for the document templates catalogue (RF-PLA-001).

Every invariant lives here, never in views or serializers (AGENTS.md #8).

Uniqueness is delegated to the database constraint and translated back into a
``DomainError`` by ``unique_violation_as``. Reading first and writing afterwards
would leave a window for two concurrent requests to both pass the check.
"""

from django.db import transaction

from apps.audit.services import record_event
from apps.common.db import unique_violation_as
from apps.common.models import DomainError
from apps.documents.models import DocumentTemplate


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
    return template


@transaction.atomic
def update_document_template(*, template, name=None, description=None, kind=None, actor=None):
    """Update the descriptive attributes of a document template. The code is immutable."""
    if name is not None:
        name = _clean_name(name)
    if description is not None:
        description = description.strip()

    return _changed(
        template,
        actor,
        "documents.template.updated",
        name=name,
        description=description,
        kind=kind,
    )


@transaction.atomic
def deactivate_document_template(*, template, actor=None):
    """Deactivate a document template instead of deleting it. Idempotent."""
    if not template.is_active:
        return template

    template.is_active = False
    template.save(update_fields=["is_active", "updated_at"])
    _audit(actor, "documents.template.deactivated", template)
    return template
