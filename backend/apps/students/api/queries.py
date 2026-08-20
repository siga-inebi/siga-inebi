"""
Read-side query helpers for the student-records domain.

Kept independent from ``apps.academics.api.queries`` on purpose: no model
here descends from ``Institution``, and importing across domains would
couple student-records to institutional-structure for no real reason
(AGENTS.md #9). The shape mirrors the academics helpers so the two domains
stay easy to read side by side.
"""

from rest_framework.exceptions import NotFound

from apps.students.models import EmergencyContact, Student, StudentHealthNote, StudentObservation


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


def _get(queryset, public_id, label):
    try:
        return queryset.get(public_id=public_id)
    except queryset.model.DoesNotExist as exc:
        raise NotFound(f"No se encontro {label}.") from exc
    except (ValueError, TypeError) as exc:  # malformed public_id
        raise NotFound(f"No se encontro {label}.") from exc


def student_or_404(public_id):
    return _get(Student.objects.all(), public_id, "el estudiante")


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


def health_notes(student, request):
    return _filter_active(
        StudentHealthNote.objects.filter(student=student).select_related("student", "author"),
        request,
    )


def health_note_or_404(public_id):
    return _get(
        StudentHealthNote.objects.select_related("student", "author").all(),
        public_id,
        "Student health note",
    )


def observations(student, request):
    return _filter_active(
        StudentObservation.objects.filter(student=student).select_related("student", "author"),
        request,
    )


def observation_or_404(public_id):
    return _get(
        StudentObservation.objects.select_related("student", "author"),
        public_id,
        "Student observation",
    )
