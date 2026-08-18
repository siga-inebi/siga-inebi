from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.common.models import DomainError
from apps.people.models import Person
from apps.students.models import (
    EmergencyContact,
    Guardian,
    Student,
    StudentGuardianRelation,
    StudentHealthNote,
)


def create_student(*, person_data, student_code, status=None, actor=None):
    student_code = _clean_text(student_code, field="student code")
    with transaction.atomic():
        person = Person.objects.create(**person_data)
        student = Student.objects.create(
            person=person,
            student_code=student_code,
            status=status or Student.StudentStatus.PRE_ENROLLED,
        )
        record_event(
            actor=actor,
            action="students.student.created",
            resource="Student",
            resource_identifier=str(student.pk),
            context={"student_code": student.student_code},
        )
    return student


def update_student(*, student, actor=None, **changes):
    """Update basic student data through the domain layer and audit supplied fields."""
    allowed_fields = {"student_code", "status", "photo"}
    supplied = {name: value for name, value in changes.items() if name in allowed_fields}
    if "student_code" in supplied:
        supplied["student_code"] = _clean_text(supplied["student_code"], field="student code")
    if "status" in supplied and supplied["status"] not in Student.StudentStatus.values:
        raise DomainError("Student status is invalid.")
    if "photo" in supplied:
        content_type = getattr(supplied["photo"], "content_type", "")
        if content_type and not content_type.startswith("image/"):
            raise DomainError("Student photo must be an image.")
    if not supplied:
        return student

    before = {name: getattr(student, name) for name in supplied if name != "photo"}
    for name, value in supplied.items():
        setattr(student, name, value)
    student.save(update_fields=[*supplied, "updated_at"])
    after = {name: getattr(student, name) for name in supplied if name != "photo"}
    record_event(
        actor=actor,
        action="students.student.updated",
        resource="Student",
        resource_identifier=str(student.pk),
        context={"fields": sorted(supplied), "before": before, "after": after},
    )
    return student


def create_guardian(*, person_data, actor=None):
    with transaction.atomic():
        person = Person.objects.create(**person_data)
        guardian = Guardian.objects.create(person=person)
        record_event(
            actor=actor,
            action="students.guardian.created",
            resource="Guardian",
            resource_identifier=str(guardian.pk),
            context={"public_id": str(guardian.public_id)},
        )
    return guardian


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
    # ``when`` is deliberately ignored. A terminated relationship must never
    # restore access to historical student information.
    from apps.identity.scopes import guardian_student_queryset

    return guardian_student_queryset(user=user).filter(pk=student.pk).exists()


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


@transaction.atomic
def create_student_guardian_relation(
    *, student, guardian, relationship_label, starts_at=None, actor=None
):
    """Create a current guardian link, making the first current link primary."""
    starts_at = starts_at or timezone.localdate()
    if starts_at > timezone.localdate():
        raise DomainError("A guardian relationship cannot start in the future.")

    relationship_label = _clean_text(relationship_label, field="relationship label")
    student = Student.objects.select_for_update().get(pk=student.pk)
    current_relations = StudentGuardianRelation.objects.select_for_update().filter(
        student=student,
        ends_at__isnull=True,
    )
    is_primary = not current_relations.filter(is_primary=True).exists()
    relation = StudentGuardianRelation.objects.create(
        student=student,
        guardian=guardian,
        relationship_label=relationship_label,
        is_primary=is_primary,
        starts_at=starts_at,
    )
    _audit(
        actor,
        "students.student_guardian_relation.created",
        relation,
        student_id=student.pk,
        guardian_id=guardian.pk,
        is_primary=is_primary,
    )
    return relation


@transaction.atomic
def change_primary_student_guardian_relation(*, relation, actor=None):
    """Atomically select one current relationship as the student's primary link."""
    student = Student.objects.select_for_update().get(pk=relation.student_id)
    relations = StudentGuardianRelation.objects.select_for_update().filter(
        student=student,
        ends_at__isnull=True,
    )
    relation = relations.filter(pk=relation.pk).first()
    if relation is None or not relation.is_active:
        raise DomainError("Only a current active guardian relationship can be primary.")

    relations.filter(is_primary=True).exclude(pk=relation.pk).update(
        is_primary=False,
        updated_at=timezone.now(),
    )
    if not relation.is_primary:
        relation.is_primary = True
        relation.save(update_fields=["is_primary", "updated_at"])
    _audit(
        actor,
        "students.student_guardian_relation.primary_changed",
        relation,
        student_id=student.pk,
        guardian_id=relation.guardian_id,
    )
    return relation


@transaction.atomic
def end_student_guardian_relation(*, relation, replacement_relation=None, actor=None):
    """End a link without deleting history and preserve one current primary link."""
    student = Student.objects.select_for_update().get(pk=relation.student_id)
    relations = StudentGuardianRelation.objects.select_for_update().filter(student=student)
    relation = relations.filter(pk=relation.pk, ends_at__isnull=True).first()
    if relation is None:
        raise DomainError("The guardian relationship is already ended.")

    replacement = None
    if replacement_relation is not None:
        replacement = relations.filter(
            pk=replacement_relation.pk,
            ends_at__isnull=True,
            is_active=True,
            starts_at__lte=timezone.localdate(),
        ).first()
        if replacement is None or replacement.pk == relation.pk:
            raise DomainError("Replacement must be another current relationship for this student.")

    if relation.is_primary:
        if replacement is None:
            raise DomainError(
                "A replacement primary relationship is required before ending the primary."
            )
        change_primary_student_guardian_relation(relation=replacement, actor=actor)

    relation.ends_at = timezone.localdate()
    relation.is_primary = False
    relation.save(update_fields=["ends_at", "is_primary", "updated_at"])
    _audit(
        actor,
        "students.student_guardian_relation.ended",
        relation,
        student_id=student.pk,
        guardian_id=relation.guardian_id,
        replacement_relation_id=getattr(replacement, "pk", None),
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


@transaction.atomic
def create_student_health_note(*, student, content, actor, recorded_on=None):
    _require_active(student, "Student")
    content = _clean_text(content, field="content")
    recorded_on = recorded_on or timezone.localdate()
    if recorded_on > timezone.localdate():
        raise DomainError("A health note cannot be recorded in the future.")
    note = StudentHealthNote.objects.create(
        student=student, author=actor, content=content, recorded_on=recorded_on
    )
    _audit(actor, "students.health_note.created", note, student_id=student.pk)
    return note


def deactivate_student_health_note(*, health_note, actor):
    health_note.is_active = False
    health_note.save(update_fields=["is_active", "updated_at"])
    _audit(
        actor,
        "students.health_note.deactivated",
        health_note,
        student_id=health_note.student_id,
    )
    return health_note
