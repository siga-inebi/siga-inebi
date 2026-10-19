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


def students(*, include_inactive=True, status=None):
    queryset = _filter_active(
        Student.objects.select_related("person"), include_inactive=include_inactive
    )
    return queryset if status is None else queryset.filter(status=status)


def guardians(*, include_inactive=True):
    from apps.students.models import Guardian

    return _filter_active(
        Guardian.objects.select_related("person"), include_inactive=include_inactive
    )


def guardian_relations(*, student_public_id=None):
    from apps.students.models import StudentGuardianRelation

    queryset = StudentGuardianRelation.objects.select_related("student", "guardian__person")
    if student_public_id is not None:
        queryset = queryset.filter(student__public_id=student_public_id)
    return queryset


def guardian_relations_for_record(*, actor, student_public_id, replacement_for=None):
    from django.db.models import BooleanField, Value
    from django.utils import timezone

    from apps.identity.scopes import authorized_student_queryset, can_access_student

    student = _get(
        authorized_student_queryset(user=actor, codename="student_view_basic"),
        student_public_id,
        "Student",
    )
    queryset = guardian_relations().filter(student=student)
    if replacement_for is not None:
        if not queryset.filter(pk=replacement_for).exists():
            raise ResourceNotFoundError("Student guardian relation not found.")
        queryset = queryset.filter(
            ends_at__isnull=True, is_active=True, starts_at__lte=timezone.localdate()
        ).exclude(pk=replacement_for)
    can_manage = can_access_student(user=actor, codename="student_edit_basic", student=student)
    return queryset.annotate(
        record_can_manage=Value(can_manage, output_field=BooleanField())
    ).order_by("-is_primary", "pk")


def emergency_contacts(student, *, include_inactive=False):
    # Orden explicito: el listado se pagina, y sin el dos paginas pueden repetir u
    # omitir contactos (INC-009). `id` desempata nombres iguales.
    return _filter_active(
        EmergencyContact.objects.filter(student=student).select_related("student"),
        include_inactive=include_inactive,
    ).order_by("name", "id")


def emergency_contact_or_404(public_id):
    return _get(
        EmergencyContact.objects.select_related("student").all(), public_id, "EmergencyContact"
    )


def health_notes(student, *, include_inactive=False):
    return _filter_active(
        StudentHealthNote.objects.filter(student=student).select_related("student", "author"),
        include_inactive=include_inactive,
    ).order_by("-recorded_on", "-created_at", "-pk")


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
    ).order_by("-observed_on", "-created_at", "-pk")


def observation_or_404(public_id):
    return _get(
        StudentObservation.objects.select_related("student", "author"),
        public_id,
        "Student observation",
    )
