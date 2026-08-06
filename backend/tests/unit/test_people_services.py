import pytest

from apps.audit.models import AuditEvent
from apps.people.services import create_person, deactivate_person, update_person
from tests.factories.identity import UserFactory
from tests.factories.people import PersonFactory


@pytest.mark.unit
@pytest.mark.django_db
def test_create_person_persists_supplied_fields():
    actor = UserFactory()

    person = create_person(
        actor=actor,
        first_name="Ana",
        last_name="Gomez",
        email="ana@example.test",
        phone_number="55512345",
        institutional_identifier="INEBI-001",
    )

    person.refresh_from_db()
    assert person.first_name == "Ana"
    assert person.last_name == "Gomez"
    assert person.email == "ana@example.test"
    assert person.phone_number == "55512345"
    assert person.institutional_identifier == "INEBI-001"
    assert person.is_active is True


@pytest.mark.unit
@pytest.mark.django_db
def test_create_person_defaults_optional_fields_to_blank():
    person = create_person(actor=None, first_name="Ana", last_name="Gomez")

    assert person.email == ""
    assert person.phone_number == ""
    assert person.institutional_identifier == ""


@pytest.mark.unit
@pytest.mark.django_db
def test_create_person_records_audit_event():
    actor = UserFactory()

    person = create_person(actor=actor, first_name="Ana", last_name="Gomez")

    event = AuditEvent.objects.get(resource="Person", resource_identifier=str(person.pk))
    assert event.action == "people.person.created"
    assert event.actor_id == actor.pk


@pytest.mark.unit
@pytest.mark.django_db
def test_update_person_applies_only_supplied_fields():
    person = PersonFactory(first_name="Old", phone_number="000")

    update_person(person=person, actor=None, first_name="New")

    person.refresh_from_db()
    assert person.first_name == "New"
    assert person.phone_number == "000"


@pytest.mark.unit
@pytest.mark.django_db
def test_update_person_can_clear_optional_field_with_empty_string():
    person = PersonFactory(phone_number="555")

    update_person(person=person, actor=None, phone_number="")

    person.refresh_from_db()
    assert person.phone_number == ""


@pytest.mark.unit
@pytest.mark.django_db
def test_update_person_records_audit_event_with_changed_fields():
    person = PersonFactory()
    actor = UserFactory()

    update_person(person=person, actor=actor, last_name="Updated")

    event = AuditEvent.objects.get(
        resource="Person", resource_identifier=str(person.pk), action="people.person.updated"
    )
    assert event.actor_id == actor.pk
    assert event.context["fields"] == ["last_name"]


@pytest.mark.unit
@pytest.mark.django_db
def test_update_person_without_changes_is_a_no_op():
    person = PersonFactory(first_name="Same")

    result = update_person(person=person, actor=None)

    assert result is person
    assert AuditEvent.objects.filter(resource="Person", action="people.person.updated").count() == 0


@pytest.mark.unit
@pytest.mark.django_db
def test_deactivate_person_sets_is_active_false():
    person = PersonFactory()

    deactivate_person(person=person, actor=None)

    person.refresh_from_db()
    assert person.is_active is False


@pytest.mark.unit
@pytest.mark.django_db
def test_deactivate_person_records_audit_event():
    person = PersonFactory()
    actor = UserFactory()

    deactivate_person(person=person, actor=actor)

    event = AuditEvent.objects.get(resource="Person", resource_identifier=str(person.pk))
    assert event.action == "people.person.deactivated"
    assert event.actor_id == actor.pk


@pytest.mark.unit
@pytest.mark.django_db
def test_deactivate_person_is_idempotent():
    person = PersonFactory(is_active=False)

    result = deactivate_person(person=person, actor=None)

    assert result is person
    assert AuditEvent.objects.filter(resource="Person").count() == 0
