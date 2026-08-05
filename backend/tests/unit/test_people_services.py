import pytest

from apps.audit.models import AuditEvent
from apps.people.services import deactivate_person
from tests.factories.identity import UserFactory
from tests.factories.people import PersonFactory


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
