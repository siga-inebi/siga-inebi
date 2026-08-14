"""
Read-side query helpers for the documents API.

Every list and detail payload is built from the querysets defined here.
"""

from rest_framework.exceptions import NotFound

from apps.academics.api.queries import resolve_institution
from apps.documents.models import DocumentTemplate
from apps.enrolments.models import Enrolment

__all__ = [
    "resolve_institution",
    "document_templates",
    "document_template_or_404",
    "document_template_versions",
    "enrolment_or_404",
]


def _wants_inactive(request):
    return str(request.query_params.get("include_inactive", "")).lower() in {
        "1",
        "true",
        "yes",
    }


def _filter_active(queryset, request):
    if _wants_inactive(request):
        return queryset
    return queryset.filter(is_active=True)


def document_templates_all(institution):
    return DocumentTemplate.objects.filter(institution=institution).order_by("name")


def document_templates(institution, request):
    return _filter_active(document_templates_all(institution), request)


def document_template_or_404(institution, public_id):
    try:
        return document_templates_all(institution).get(public_id=public_id)
    except DocumentTemplate.DoesNotExist as exc:
        raise NotFound("DocumentTemplate not found.") from exc
    except (ValueError, TypeError) as exc:  # malformed public_id
        raise NotFound("DocumentTemplate not found.") from exc


def document_template_versions(template):
    return template.versions.all()


def enrolment_or_404(public_id):
    try:
        return Enrolment.objects.get(public_id=public_id)
    except Enrolment.DoesNotExist as exc:
        raise NotFound("Enrolment not found.") from exc
    except (ValueError, TypeError) as exc:  # malformed public_id
        raise NotFound("Enrolment not found.") from exc
