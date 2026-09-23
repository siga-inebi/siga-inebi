"""RF-AUL-006 (#104): preserve classrooms referenced by previous school cycles.

Acceptance scenarios: reject physical deletion (instance and queryset), keep
historical references and audit on API deactivation, and reject unauthenticated
attempts without changing the classroom or its history.
"""

from datetime import date

import pytest
from django.db.models.deletion import ProtectedError
from django.urls import reverse

from apps.academics.models import AcademicCycle, Classroom
from apps.audit.models import AuditEvent
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    ClassroomFactory,
    ClassSessionFactory,
    SectionFactory,
    ShiftFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture(params=["session", "default_classroom"])
def historical_classroom(request, institution):
    """Both historical relations protect an aula, even when inactive."""
    previous = AcademicCycleFactory(
        institution=institution,
        starts_on=date(2025, 1, 1),
        ends_on=date(2025, 12, 31),
        status=AcademicCycle.CycleStatus.CLOSED,
    )
    AcademicCycleFactory(
        institution=institution,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 12, 31),
    )
    campus = CampusFactory(institution=institution)
    classroom = ClassroomFactory(campus=campus)
    section = SectionFactory(academic_cycle=previous, shift=ShiftFactory(campus=campus))
    if request.param == "session":
        reference = ClassSessionFactory(
            section=section, classroom=classroom, starts_on=previous.starts_on, is_active=False
        )
        field = "classroom_id"
    else:
        section.default_classroom = classroom
        section.is_active = False
        section.save(update_fields=["default_classroom", "is_active"])
        reference = section
        field = "default_classroom_id"
    return classroom, reference, field


@pytest.mark.parametrize("bulk", [False, True], ids=["instance", "queryset"])
def test_physical_deletion_rejects_previous_cycle_references(historical_classroom, bulk):
    classroom, reference, field = historical_classroom
    classroom.is_active = False
    classroom.save(update_fields=["is_active"])

    with pytest.raises(ProtectedError):
        if bulk:
            Classroom.objects.filter(pk=classroom.pk).delete()
        else:
            classroom.delete()

    classroom.refresh_from_db()
    reference.refresh_from_db()
    assert classroom.is_active is False
    assert getattr(reference, field) == classroom.pk


@pytest.mark.api
def test_api_deactivation_preserves_previous_cycle_history_and_audit(
    auth_client, historical_classroom
):
    classroom, reference, field = historical_classroom
    detail_url = reverse("classroom-detail", args=[classroom.public_id])

    response = auth_client.delete(detail_url)

    assert response.status_code == 204
    classroom.refresh_from_db()
    reference.refresh_from_db()
    assert classroom.is_active is False
    assert getattr(reference, field) == classroom.pk
    detail = auth_client.get(detail_url)
    assert detail.status_code == 200
    assert detail.json()["public_id"] == str(classroom.public_id)
    assert detail.json()["is_active"] is False
    event = AuditEvent.objects.get(
        action="academics.classroom.deactivated", resource_identifier=str(classroom.pk)
    )
    assert event.actor_id == auth_client.user.pk
    assert event.context["code"] == classroom.code


@pytest.mark.api
def test_unauthenticated_deactivation_preserves_history(client, historical_classroom):
    classroom, reference, field = historical_classroom

    response = client.delete(reverse("classroom-detail", args=[classroom.public_id]))

    assert response.status_code == 403
    classroom.refresh_from_db()
    reference.refresh_from_db()
    assert classroom.is_active is True
    assert getattr(reference, field) == classroom.pk
    assert not AuditEvent.objects.filter(action="academics.classroom.deactivated").exists()
