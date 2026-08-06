from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.common.models import DomainError
from apps.students.models import EmergencyContact

# --------------------------------------------------------------------------- #
# helpers
#
# Intentionally not imported from apps.academics.services: same shape, but
# student-records stays independent of institutional-structure (AGENTS.md #9).
# --------------------------------------------------------------------------- #


def _clean_text(value, *, field):
    text = (value or "").strip()
    if not text:
        raise DomainError(f"A non-empty {field} is required.")
    return text


def _require_active(instance, label):
    if not instance.is_active:
        raise DomainError(f"{label} '{instance}' is inactive and cannot be used.")


def _audit(actor, action, instance, **context):
    record_event(
        actor=actor,
        action=action,
        resource=type(instance).__name__,
        resource_identifier=str(instance.pk),
        context=context,
    )


def _changed(instance, actor, action, **candidates):
    """
    Apply the fields whose value was actually supplied, persist only those, and
    audit what changed. ``None`` means "not supplied", never "set to null".
    """
    fields = [name for name, value in candidates.items() if value is not None]
    for name in fields:
        setattr(instance, name, candidates[name])

    instance.save(update_fields=[*fields, "updated_at"])
    _audit(actor, action, instance, fields=fields)
    return instance


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


# --------------------------------------------------------------------------- #
# emergency contacts (RF-EXP-005)
# --------------------------------------------------------------------------- #


@transaction.atomic
def create_emergency_contact(*, student, name, phone_number, relationship_label, actor=None):
    """
    Register an emergency contact for a student.

    Rules:
    - The student must be active.
    - Name, phone number and relationship label cannot be blank.
    """
    _require_active(student, "Student")
    name = _clean_text(name, field="name")
    phone_number = _clean_text(phone_number, field="phone_number")
    relationship_label = _clean_text(relationship_label, field="relationship_label")

    contact = EmergencyContact.objects.create(
        student=student,
        name=name,
        phone_number=phone_number,
        relationship_label=relationship_label,
    )
    _audit(actor, "students.emergency_contact.created", contact, student_id=student.pk)
    return contact


def update_emergency_contact(
    *, emergency_contact, name=None, phone_number=None, relationship_label=None, actor=None
):
    """Update the supplied fields only. ``None`` means "not supplied", never "set to null"."""
    if name is not None:
        name = _clean_text(name, field="name")
    if phone_number is not None:
        phone_number = _clean_text(phone_number, field="phone_number")
    if relationship_label is not None:
        relationship_label = _clean_text(relationship_label, field="relationship_label")

    candidates = {
        "name": name,
        "phone_number": phone_number,
        "relationship_label": relationship_label,
    }
    if not any(value is not None for value in candidates.values()):
        return emergency_contact

    return _changed(emergency_contact, actor, "students.emergency_contact.updated", **candidates)
