"""Read-side queries for the documents domain."""

from django.db.models import OuterRef, Subquery

from apps.common.exceptions import ResourceNotFoundError
from apps.documents.models import (
    DocumentIssuance,
    DocumentKind,
    DocumentRecord,
    DocumentTemplate,
    DocumentTemplateVersion,
)
from apps.enrolments.models import Enrolment
from apps.students.models import Student
from apps.teachers.models import Teacher


def _filter_active(queryset, *, include_inactive=False):
    return queryset if include_inactive else queryset.filter(is_active=True)


def document_kinds_all(institution):
    return DocumentKind.objects.filter(institution=institution).order_by("label")


def document_kinds(institution, *, include_inactive=False):
    return _filter_active(document_kinds_all(institution), include_inactive=include_inactive)


def document_kind_or_404(institution, public_id):
    try:
        return document_kinds_all(institution).get(public_id=public_id)
    except DocumentKind.DoesNotExist as exc:
        raise ResourceNotFoundError("No se encontró el tipo de documento.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("No se encontró el tipo de documento.") from exc


def document_templates_all(institution):
    return (
        DocumentTemplate.objects.filter(institution=institution)
        .select_related("document_kind")
        .order_by("name")
    )


def document_templates(institution, *, include_inactive=False):
    return _filter_active(document_templates_all(institution), include_inactive=include_inactive)


def document_template_or_404(institution, public_id):
    try:
        return document_templates_all(institution).get(public_id=public_id)
    except DocumentTemplate.DoesNotExist as exc:
        raise ResourceNotFoundError("No se encontró la plantilla.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("No se encontró la plantilla.") from exc


def document_template_versions(template):
    return template.versions.all()


def template_issuance_uses(institution):
    latest = DocumentTemplateVersion.objects.filter(template_id=OuterRef("pk")).order_by(
        "-sequence"
    )
    templates = (
        DocumentTemplate.objects.filter(institution=institution, is_active=True)
        .exclude(issuance_use=DocumentTemplate.IssuanceUse.NONE)
        .annotate(latest_content=Subquery(latest.values("content")[:1]))
    )
    active = {template.issuance_use: template for template in templates}
    result = []
    for code, label in DocumentTemplate.IssuanceUse.choices:
        if code == DocumentTemplate.IssuanceUse.NONE:
            continue
        template = active.get(code)
        result.append(
            {
                "code": code,
                "label": label,
                "active_template": {"public_id": template.public_id, "name": template.name}
                if template
                else None,
                "uses_fallback": not template or not (template.latest_content or "").strip(),
            }
        )
    return result


def enrolment_or_404(public_id):
    try:
        return Enrolment.objects.get(public_id=public_id)
    except Enrolment.DoesNotExist as exc:
        raise ResourceNotFoundError("No se encontró la matrícula.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("No se encontró la matrícula.") from exc


def student_or_404(public_id):
    try:
        return Student.objects.get(public_id=public_id)
    except Student.DoesNotExist as exc:
        raise ResourceNotFoundError("No se encontró el estudiante.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("No se encontró el estudiante.") from exc


def document_record_or_404(public_id):
    try:
        return DocumentRecord.objects.select_related("student", "teacher", "enrolment").get(
            public_id=public_id
        )
    except DocumentRecord.DoesNotExist as exc:
        raise ResourceNotFoundError("No se encontró el documento.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("No se encontró el documento.") from exc


def document_records_for_enrolment(enrolment):
    return DocumentRecord.objects.filter(enrolment=enrolment).order_by(
        "version_group_id", "-version_number"
    )


def document_records_for_student(student):
    return (
        DocumentRecord.objects.filter(student=student)
        .select_related("enrolment")
        .order_by("-created_at", "-pk")
    )


def document_issuance_or_404(public_id):
    try:
        return DocumentIssuance.objects.select_related("student").get(public_id=public_id)
    except DocumentIssuance.DoesNotExist as exc:
        raise ResourceNotFoundError("No se encontró la emisión.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("No se encontró la emisión.") from exc


def teacher_or_404(public_id):
    try:
        return Teacher.objects.select_related("person").get(public_id=public_id)
    except Teacher.DoesNotExist as exc:
        raise ResourceNotFoundError("No se encontró el docente.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("No se encontró el docente.") from exc


def document_records_for_teacher(teacher):
    """Every version of every document in a teacher's dossier (RF-DOC-001)."""
    return DocumentRecord.objects.filter(teacher=teacher).order_by(
        "version_group_id", "-version_number"
    )
