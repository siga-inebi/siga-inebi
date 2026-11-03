import pytest

from apps.academics.services import create_classroom, deactivate_classroom, update_classroom
from apps.audit.models import AuditEvent
from apps.common.exceptions import DomainError
from tests.factories.academic import CampusFactory, ClassroomFactory
from tests.factories.identity import UserFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_classroom_changes_are_audited_with_the_changed_values():
    actor = UserFactory()
    campus = CampusFactory()

    classroom = create_classroom(
        campus=campus,
        name="Aula 101",
        code="a-101",
        location="Primer nivel",
        capacity=25,
        actor=actor,
    )
    update_classroom(classroom=classroom, location="Segundo nivel", capacity=30, actor=actor)
    deactivate_classroom(classroom=classroom, actor=actor)

    created = AuditEvent.objects.get(action="academics.classroom.created")
    updated = AuditEvent.objects.get(action="academics.classroom.updated")
    deactivated = AuditEvent.objects.get(action="academics.classroom.deactivated")

    assert classroom.code == "A-101"
    assert created.actor == actor
    assert updated.context["changes"] == {
        "location": {"before": "Primer nivel", "after": "Segundo nivel"},
        "capacity": {"before": 25, "after": 30},
    }
    assert deactivated.resource_identifier == str(classroom.pk)


def test_classroom_rejects_inactive_campus_and_duplicate_code():
    inactive = CampusFactory(is_active=False)

    with pytest.raises(DomainError, match="inactivo"):
        create_classroom(campus=inactive, name="Aula 1", code="A-1")

    campus = CampusFactory()
    ClassroomFactory(campus=campus, code="A-1")
    with pytest.raises(DomainError, match="ya existe"):
        create_classroom(campus=campus, name="Aula duplicada", code="a-1")
