"""Read-side queries for the documents domain."""

from apps.common.exceptions import ResourceNotFoundError
from apps.documents.models import DocumentTemplate
from apps.enrolments.models import Enrolment


def _filter_active(queryset, *, include_inactive=False):
    return queryset if include_inactive else queryset.filter(is_active=True)


def document_templates_all(institution):
    return DocumentTemplate.objects.filter(institution=institution).order_by("name")


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
