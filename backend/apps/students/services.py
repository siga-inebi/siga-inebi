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


def deactivate_guardian(*, guardian, actor=None):
    guardian.is_active = False
    guardian.save(update_fields=["is_active", "updated_at"])
    record_event(
        actor=actor,
        action="students.guardian.deactivated",
        resource="Guardian",
        resource_identifier=str(guardian.pk),
        context={"public_id": str(guardian.public_id)},
    )
    return guardian


def deactivate_emergency_contact(*, emergency_contact, actor=None):
    emergency_contact.is_active = False
    emergency_contact.save(update_fields=["is_active", "updated_at"])
    record_event(
        actor=actor,
        action="students.emergency_contact.deactivated",
        resource="EmergencyContact",
        resource_identifier=str(emergency_contact.pk),
        context={"public_id": str(emergency_contact.public_id)},
    )
    return emergency_contact


def end_student_guardian_relation(*, relation, actor=None, ends_at=None):
    ends_at = ends_at or timezone.localdate()
    relation.ends_at = ends_at
    relation.save(update_fields=["ends_at", "updated_at"])
    record_event(
        actor=actor,
        action="students.student_guardian_relation.ended",
        resource="StudentGuardianRelation",
        resource_identifier=str(relation.pk),
        context={"student_id": relation.student_id, "guardian_id": relation.guardian_id},
    )
    return relation
