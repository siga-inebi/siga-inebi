"""
Read-side query helpers for the student-records domain.

Kept independent from ``apps.academics.api.queries`` on purpose: no model
here descends from ``Institution``, and importing across domains would
couple student-records to institutional-structure for no real reason
(AGENTS.md #9). The shape mirrors the academics helpers so the two domains
stay easy to read side by side.
"""

from rest_framework.exceptions import NotFound

from apps.students.models import EmergencyContact, Guardian, Student, StudentGuardianRelation


def _wants_inactive(request):
    return str(request.query_params.get("include_inactive", "")).lower() in {
        "1",
        "true",
        "yes",
    }


def _filter_active(queryset, request):
    """``include_inactive`` filters on the ``is_active`` field."""
    if _wants_inactive(request):
        return queryset
    return queryset.filter(is_active=True)


def _filter_open(queryset, request):
    """
    Same ``include_inactive`` contract as ``_filter_active``, but for models
    whose real lifecycle flag is ``ends_at`` rather than ``is_active`` (see
    ``StudentGuardianRelation``). Filtering on ``is_active`` there would never
    hide anything: that field is never set on this model.
    """
    if _wants_inactive(request):
        return queryset
    return queryset.filter(ends_at__isnull=True)


def _get(queryset, public_id, label):
    try:
        return queryset.get(public_id=public_id)
    except queryset.model.DoesNotExist as exc:
        raise NotFound(f"{label} not found.") from exc
    except (ValueError, TypeError) as exc:  # malformed public_id
        raise NotFound(f"{label} not found.") from exc


def student_or_404(public_id):
    return _get(Student.objects.all(), public_id, "Student")


def guardian_options(request):
    """Active guardians, for populating a "link existing guardian" selector."""
    return (
        Guardian.objects.filter(is_active=True)
        .select_related("person")
        .order_by("person__last_name", "person__first_name")
    )


def emergency_contacts(student, request):
    return _filter_active(
        EmergencyContact.objects.filter(student=student).select_related("student"), request
    )


def emergency_contact_or_404(public_id):
    return _get(
        EmergencyContact.objects.select_related("student").all(),
        public_id,
        "EmergencyContact",
    )


def student_guardian_relations(student, request):
    return _filter_open(
        StudentGuardianRelation.objects.filter(student=student).select_related(
            "student", "guardian__person"
        ),
        request,
    )


def student_guardian_relation_or_404(public_id):
    return _get(
        StudentGuardianRelation.objects.select_related("student", "guardian__person").all(),
        public_id,
        "StudentGuardianRelation",
    )
