from django.utils import timezone

from apps.audit.services import record_event


def guardian_can_access_student(*, user, student, when=None):
    when = when or timezone.localdate()
    person = getattr(user, "person", None)
    guardian = getattr(person, "guardian_profile", None)
    if guardian is None:
        return False

    return (
        guardian.student_relations.filter(
            student=student,
            starts_at__lte=when,
        )
        .filter(ends_at__isnull=True)
        .exists()
        or guardian.student_relations.filter(
            student=student,
            starts_at__lte=when,
            ends_at__gte=when,
        ).exists()
    )


def deactivate_student(*, student, actor=None):
    student.is_active = False
    student.status = student.StudentStatus.INACTIVE
    student.save(update_fields=["is_active", "status", "updated_at"])
    record_event(
        actor=actor,
        action="students.student.deactivated",
        resource="Student",
        resource_identifier=str(student.pk),
        context={"student_code": student.student_code},
    )
    return student
