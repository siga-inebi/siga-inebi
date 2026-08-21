"""Read-side queries for the student-records domain."""

from apps.common.exceptions import ResourceNotFoundError
from apps.students.models import EmergencyContact, Student, StudentHealthNote, StudentObservation


def _filter_active(queryset, *, include_inactive=False):
    return queryset if include_inactive else queryset.filter(is_active=True)


def _get(queryset, public_id, label):
    try:
        return queryset.get(public_id=public_id)
    except queryset.model.DoesNotExist as exc:
        raise ResourceNotFoundError(f"{label} not found.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError(f"{label} not found.") from exc


def student_or_404(public_id):
    return _get(Student.objects.all(), public_id, "Student")


def students():
    return Student.objects.all()


def guardians():
    from apps.students.models import Guardian

    return Guardian.objects.select_related("person").all()


def guardian_relations():
    from apps.students.models import StudentGuardianRelation

    return StudentGuardianRelation.objects.select_related("student", "guardian__person")


def emergency_contacts(student, *, include_inactive=False):
    return _filter_active(
        EmergencyContact.objects.filter(student=student).select_related("student"),
        include_inactive=include_inactive,
    )


def emergency_contact_or_404(public_id):
    return _get(
        EmergencyContact.objects.select_related("student").all(), public_id, "EmergencyContact"
    )


def health_notes(student, *, include_inactive=False):
    return _filter_active(
        StudentHealthNote.objects.filter(student=student).select_related("student", "author"),
        include_inactive=include_inactive,
    )


def health_note_or_404(public_id):
    return _get(
        StudentHealthNote.objects.select_related("student", "author").all(),
        public_id,
        "Student health note",
    )


def observations(student, *, include_inactive=False):
    return _filter_active(
        StudentObservation.objects.filter(student=student).select_related("student", "author"),
        include_inactive=include_inactive,
    )


def observation_or_404(public_id):
    return _get(
        StudentObservation.objects.select_related("student", "author"),
        public_id,
        "Student observation",
    )
