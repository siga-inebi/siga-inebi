"""
Domain services for the document templates catalogue (RF-PLA-001).

Every invariant lives here, never in views or serializers (AGENTS.md #8).

Uniqueness is delegated to the database constraint and translated back into a
``DomainError`` by ``unique_violation_as``. Reading first and writing afterwards
would leave a window for two concurrent requests to both pass the check.
"""

import os
import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Max

from apps.audit.services import diff_fields, record_event
from apps.common.db import unique_violation_as
from apps.common.models import DomainError
from apps.documents.field_catalog import FIELD_TAGS
from apps.documents.models import DocumentRecord, DocumentTemplate, DocumentTemplateVersion
from apps.enrolments.models import Enrolment, EnrolmentDocumentRequirement
from apps.enrolments.services import pending_required_document_codes

SENSITIVE_FIELD_TAGS_PERMISSION = "student_view_sensitive"
OFFICIAL_ISSUANCE_PERMISSION = "document_issue"
DOCUMENT_READ_PERMISSION = "document_read"
ALLOWED_DOCUMENT_CONTENT_TYPES = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
}


def normalize_document_filename(filename):
    """Return a safe, deterministic, lowercase basename for persisted storage names."""
    original = (filename or "document").strip()
    name = os.path.basename(original)
    stem = Path(name).stem
    suffix = Path(name).suffix.lower()

    normalized_stem = re.sub(r"[^a-z0-9]+", "-", (stem or "document").lower()).strip("-_.")
    if not normalized_stem:
        normalized_stem = "document"

    if suffix in {".pdf", ".jpg", ".jpeg", ".png"}:
        return f"{normalized_stem}{suffix}"

    # The caller must validate the extension before using the output; this keeps the
    # normalization deterministic without inventing a new storage policy.
    return f"{normalized_stem}.pdf"


def validate_document_upload(upload):
    """Validate uploaded documents against the documented file storage rules."""
    if upload is None:
        raise DomainError("A document upload is required.")

    original_name = getattr(upload, "name", "") or "document"
    content_type = (getattr(upload, "content_type", "") or "").lower()
    payload = upload.read()
    size_bytes = len(payload)
    upload.seek(0)

    if not payload:
        raise DomainError("Uploaded document is empty.")

    suffix = Path(original_name).suffix.lower()
    allowed_suffixes = set().union(*(types for types in ALLOWED_DOCUMENT_CONTENT_TYPES.values()))
    if suffix not in allowed_suffixes:
        raise DomainError("Uploaded document type is not supported.")

    resolved_content_type = None
    for mime_type, suffixes in ALLOWED_DOCUMENT_CONTENT_TYPES.items():
        if suffix in suffixes:
            resolved_content_type = mime_type
            break

    if resolved_content_type is None:
        raise DomainError("Uploaded document type is not supported.")

    if content_type and content_type not in ALLOWED_DOCUMENT_CONTENT_TYPES:
        raise DomainError("Uploaded document type is not supported.")

    max_size = getattr(settings, "DOCUMENT_MAX_UPLOAD_SIZE_BYTES", 10 * 1024 * 1024)
    if size_bytes > max_size:
        raise DomainError(f"Uploaded document exceeds the maximum size of {max_size} bytes.")

    return {
        "filename": original_name,
        "normalized_filename": normalize_document_filename(original_name),
        "content_type": resolved_content_type,
        "size_bytes": size_bytes,
        "extension": suffix,
    }


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


def record_document_read_audit(
    *,
    actor,
    subject=None,
    resource=None,
    action="documents.document.read",
    context=None,
):
    """Audits a document read when the caller is allowed to access confidential dossier data."""
    subject_label = resource or type(subject).__name__ if subject is not None else "Document"
    resource_identifier = (
        str(subject.pk) if subject is not None and getattr(subject, "pk", None) is not None else ""
    )
    is_authorized = bool(
        actor and (actor.is_superuser or actor.has_atomic_permission(DOCUMENT_READ_PERMISSION))
    )
    if not is_authorized:
        record_event(
            actor=actor,
            action="documents.document.read_denied",
            resource=subject_label,
            resource_identifier=resource_identifier,
            context={"result": "denied", "reason": "missing_permission", **(context or {})},
        )
        raise PermissionDenied("Actor lacks permission to read documents.")

    record_event(
        actor=actor,
        action=action,
        resource=subject_label,
        resource_identifier=resource_identifier,
        context={"result": "success", **(context or {})},
    )
    return True


def student_document_dossier(*, student):
    """Return a consolidated view of the student's history, requirements and document records."""
    enrolments = list(
        Enrolment.objects.filter(student=student)
        .select_related("student", "academic_cycle", "grade", "section")
        .order_by("-effective_on", "-created_at", "-pk")
    )
    requirements = list(
        EnrolmentDocumentRequirement.objects.filter(enrolment__student=student)
        .select_related("enrolment")
        .order_by("-enrolment__effective_on", "code")
    )
    documents = list(
        DocumentRecord.objects.filter(student=student)
        .select_related("student", "enrolment")
        .order_by("-created_at", "-pk")
    )
    return {
        "student_id": str(student.public_id),
        "enrolments": [
            {
                "enrolment_id": str(enrolment.public_id),
                "status": enrolment.status,
                "is_active": enrolment.is_active,
                "academic_cycle_id": str(enrolment.academic_cycle.public_id),
                "grade_id": str(enrolment.grade.public_id),
                "section_id": str(enrolment.section.public_id),
                "effective_on": enrolment.effective_on.isoformat(),
                "ends_on": enrolment.ends_on.isoformat() if enrolment.ends_on else None,
            }
            for enrolment in enrolments
        ],
        "requirements": [
            {
                "enrolment_id": str(requirement.enrolment.public_id),
                "code": requirement.code,
                "name": requirement.name,
                "status": requirement.status,
                "is_required": requirement.is_required,
                "is_active": requirement.is_active,
            }
            for requirement in requirements
        ],
        "documents": [
            {
                "document_id": str(document.public_id),
                "enrolment_id": str(document.enrolment.public_id) if document.enrolment else None,
                "filename": document.filename,
                "storage_key": document.storage_key,
                "content_type": document.content_type,
                "size_bytes": document.size_bytes,
                "checksum": document.checksum,
                "status": document.status,
                "is_active": document.is_active,
                "created_at": document.created_at.isoformat(),
            }
            for document in documents
        ],
    }


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


def _audit(actor, action, instance, *, changes=None, **context):
    record_event(
        actor=actor,
        action=action,
        resource=type(instance).__name__,
        resource_identifier=str(instance.pk),
        context=context,
        changes=changes,
    )


def _changed(instance, actor, action, **candidates):
    """
    Apply the fields whose value was actually supplied, persist only those, and
    audit what changed -- including before/after values (RF-BIT-002). ``None``
    means "not supplied", never "set to null".
    """
    fields = [name for name, value in candidates.items() if value is not None]
    changes = diff_fields(instance, **candidates)  # read before mutating
    for name in fields:
        setattr(instance, name, candidates[name])

    instance.save(update_fields=[*fields, "updated_at"])
    _audit(actor, action, instance, changes=changes, fields=fields)
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


def deactivate_document_record(*, record, actor=None):
    """Retain the document record for history without hard deletion."""
    if not record.is_active:
        return record

    record.is_active = False
    record.status = DocumentRecord.StorageStatus.RETAINED
    record.save(update_fields=["is_active", "status", "updated_at"])
    _audit(actor, "documents.record.deactivated", record, storage_status=record.status)
    return record


def compile_generated_document(*, template, payload=None, persist=False, actor=None):
    """Compile a document in memory and never store generated PDFs on disk.

    RF-DOC-008 requires that generated reports and certificates remain ephemeral:
    they are assembled on demand and not persisted as a stored file record.
    """
    if persist:
        raise DomainError(
            "Generated documents are compiled in memory and must not be persisted to storage."
        )

    data = payload or {}
    student_name = str(data.get("student_name") or "Documento")
    document_type = str(data.get("document_type") or getattr(template, "name", "Documento"))
    title = f"{document_type}: {student_name}"

    rendered = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 77 >>\nstream\nBT /F1 12 Tf 30 90 Td ("
        + title.encode("utf-8")[:80]
        + b") Tj ET\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n"
        b"0000000125 00000 n\n0000000267 00000 n\n0000000780 00000 n\ntrailer\n"
        b"<< /Root 1 0 R /Size 6 >>\nstartxref\n870\n%%EOF"
    )

    _audit(
        actor,
        "documents.generated_document.compiled",
        template,
        document_type=getattr(template, "kind", "other"),
        persisted=False,
    )

    return type(
        "GeneratedDocument",
        (),
        {
            "content": rendered,
            "content_type": "application/pdf",
            "storage_key": None,
            "persisted": False,
        },
    )()


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
