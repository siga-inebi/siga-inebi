"""Read-side reference resolution for enrolment application services."""

from apps.academics.models import AcademicCycle, Grade, Section, Shift
from apps.common.exceptions import ResourceNotFoundError
from apps.enrolments.models import Enrolment, StudentMovement
from apps.students.models import Student


def _get(queryset, public_id, label):
    try:
        return queryset.get(public_id=public_id)
    except (queryset.model.DoesNotExist, ValueError, TypeError) as exc:
        raise ResourceNotFoundError(f"{label} not found.") from exc


def student_or_404(public_id):
    return _get(Student.objects.all(), public_id, "Student")


def academic_cycle_or_404(public_id):
    return _get(AcademicCycle.objects.all(), public_id, "Academic cycle")


def grade_or_404(public_id):
    return _get(Grade.objects.all(), public_id, "Grade")


def shift_or_404(public_id):
    return _get(Shift.objects.all(), public_id, "Shift")


def section_or_404(public_id):
    return _get(Section.objects.all(), public_id, "Section")


def enrolment_or_404(public_id):
    return _get(Enrolment.objects.all(), public_id, "Enrolment")


def student_movement_or_404(public_id):
    return _get(StudentMovement.objects.all(), public_id, "Student movement")


def student_movements(*, student):
    return StudentMovement.objects.filter(student=student).select_related(
        "student",
        "source_enrolment",
        "target_enrolment",
    )
