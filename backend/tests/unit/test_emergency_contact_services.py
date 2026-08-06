import pytest

from apps.audit.models import AuditEvent
from apps.common.models import DomainError
from apps.students.services import create_emergency_contact, update_emergency_contact
from tests.factories.identity import UserFactory
from tests.factories.students import EmergencyContactFactory, StudentFactory


@pytest.mark.unit
@pytest.mark.django_db
def test_create_emergency_contact_persists_supplied_fields():
    student = StudentFactory()
    actor = UserFactory()

    contact = create_emergency_contact(
        student=student,
        name="Maria Perez",
        phone_number="555-0123",
        relationship_label="Tia",
        actor=actor,
    )

    contact.refresh_from_db()
    assert contact.student_id == student.pk
    assert contact.name == "Maria Perez"
    assert contact.phone_number == "555-0123"
    assert contact.relationship_label == "Tia"
    assert contact.is_active is True


@pytest.mark.unit
@pytest.mark.django_db
def test_create_emergency_contact_records_audit_event():
    student = StudentFactory()
    actor = UserFactory()

    contact = create_emergency_contact(
        student=student,
        name="Maria Perez",
        phone_number="555-0123",
        relationship_label="Tia",
        actor=actor,
    )

    event = AuditEvent.objects.get(resource="EmergencyContact", resource_identifier=str(contact.pk))
    assert event.action == "students.emergency_contact.created"
    assert event.actor_id == actor.pk
    assert event.context["student_id"] == student.pk


@pytest.mark.unit
@pytest.mark.django_db
def test_create_emergency_contact_rejects_inactive_student():
    student = StudentFactory(is_active=False)

    with pytest.raises(DomainError):
        create_emergency_contact(
            student=student,
            name="Maria Perez",
            phone_number="555-0123",
            relationship_label="Tia",
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_create_emergency_contact_rejects_blank_name():
    student = StudentFactory()

    with pytest.raises(DomainError):
        create_emergency_contact(
            student=student,
            name="   ",
            phone_number="555-0123",
            relationship_label="Tia",
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_update_emergency_contact_applies_only_supplied_fields():
    contact = EmergencyContactFactory(name="Old", phone_number="000")

    update_emergency_contact(emergency_contact=contact, name="New")

    contact.refresh_from_db()
    assert contact.name == "New"
    assert contact.phone_number == "000"


@pytest.mark.unit
@pytest.mark.django_db
def test_update_emergency_contact_records_audit_event_with_changed_fields():
    contact = EmergencyContactFactory()
    actor = UserFactory()

    update_emergency_contact(emergency_contact=contact, name="Updated", actor=actor)

    event = AuditEvent.objects.get(
        resource="EmergencyContact",
        resource_identifier=str(contact.pk),
        action="students.emergency_contact.updated",
    )
    assert event.actor_id == actor.pk
    assert event.context["fields"] == ["name"]


@pytest.mark.unit
@pytest.mark.django_db
def test_update_emergency_contact_without_changes_is_a_no_op():
    contact = EmergencyContactFactory()

    result = update_emergency_contact(emergency_contact=contact)

    assert result is contact
    assert (
        AuditEvent.objects.filter(
            resource="EmergencyContact", action="students.emergency_contact.updated"
        ).count()
        == 0
    )
