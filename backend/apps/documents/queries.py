"""Read-side queries for the documents domain."""

from apps.common.exceptions import ResourceNotFoundError
from apps.documents.models import (
    DocumentIssuance,
    DocumentKind,
    DocumentRecord,
    DocumentTemplate,
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
        raise ResourceNotFoundError("DocumentKind not found.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("DocumentKind not found.") from exc


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
        raise ResourceNotFoundError("DocumentTemplate not found.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("DocumentTemplate not found.") from exc


def document_template_versions(template):
    return template.versions.all()


def enrolment_or_404(public_id):
    try:
        return Enrolment.objects.get(public_id=public_id)
    except Enrolment.DoesNotExist as exc:
        raise ResourceNotFoundError("Enrolment not found.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("Enrolment not found.") from exc


def student_or_404(public_id):
    try:
        return Student.objects.get(public_id=public_id)
    except Student.DoesNotExist as exc:
        raise ResourceNotFoundError("Student not found.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("Student not found.") from exc


def document_record_or_404(public_id):
    try:
        return DocumentRecord.objects.select_related("student", "teacher", "enrolment").get(
            public_id=public_id
        )
    except DocumentRecord.DoesNotExist as exc:
        raise ResourceNotFoundError("DocumentRecord not found.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("DocumentRecord not found.") from exc


def document_records_for_enrolment(enrolment):
    return DocumentRecord.objects.filter(enrolment=enrolment).order_by(
        "version_group_id", "-version_number"
    )


def document_issuance_or_404(public_id):
    try:
        return DocumentIssuance.objects.select_related("student").get(public_id=public_id)
    except DocumentIssuance.DoesNotExist as exc:
        raise ResourceNotFoundError("DocumentIssuance not found.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("DocumentIssuance not found.") from exc


def teacher_or_404(public_id):
    try:
        return Teacher.objects.select_related("person").get(public_id=public_id)
    except Teacher.DoesNotExist as exc:
        raise ResourceNotFoundError("Teacher not found.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError("Teacher not found.") from exc


def document_records_for_teacher(teacher):
    """Every version of every document in a teacher's dossier (RF-DOC-001)."""
    return DocumentRecord.objects.filter(teacher=teacher).order_by(
        "version_group_id", "-version_number"
    )
