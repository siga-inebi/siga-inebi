"""RF-AUL-005: unavailability blocks new assignments, never removes history."""

import pytest
from django.urls import reverse

from apps.academics.models import AcademicCycle
from apps.academics.services import (
    create_class_session,
    create_section,
    update_classroom,
    update_section,
)
from apps.audit.models import AuditEvent
from apps.common.exceptions import DomainError
from tests.factories.academic import (
    AcademicCycleFactory,
    CampusFactory,
    ClassroomFactory,
    ClassScheduleBlockFactory,
    SectionFactory,
    SubjectFactory,
)

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def room_context(institution):
    section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))
    classroom = ClassroomFactory(campus=section.shift.campus)
    subject = SubjectFactory(institution=institution)
    block = ClassScheduleBlockFactory(shift=section.shift)
    return (
        classroom,
        section,
        {
            "academic_cycle": section.academic_cycle,
            "section": section,
            "subject": subject,
            "schedule_block": block,
            "classroom": classroom,
        },
    )


@pytest.mark.parametrize("status", ["unavailable", "maintenance"])
def test_unavailability_preserves_sessions_and_reopening_allows_new_ones(
    auth_client, room_context, status
):
    classroom, section, payload = room_context
    session = create_class_session(**payload, day_of_week=1)
    section.default_classroom = classroom
    section.save(update_fields=["default_classroom"])
    url = reverse("classroom-detail", args=[classroom.public_id])

    response = auth_client.patch(url, {"service_status": status}, content_type="application/json")

    assert response.status_code == 200
    assert response.json()["service_status"] == status
    assert response.json()["is_active"] is True
    session.refresh_from_db()
    section.refresh_from_db()
    assert session.is_active and session.classroom_id == classroom.pk
    assert section.default_classroom_id == classroom.pk
    assert AuditEvent.objects.get(action="academics.classroom.updated").context["changes"][
        "service_status"
    ] == {"before": "available", "after": status}
    # The service must reject even when its caller holds an older model instance.
    with pytest.raises(DomainError, match="servicio"):
        create_class_session(**payload, day_of_week=2)
    rejected = auth_client.post(
        reverse("section-class-session-list-create", args=[section.public_id]),
        {
            "subject_id": str(payload["subject"].public_id),
            "schedule_block_id": str(payload["schedule_block"].public_id),
            "classroom_id": str(classroom.public_id),
            "day_of_week": 2,
        },
        content_type="application/json",
    )
    assert rejected.status_code == 400
    assert "servicio" in str(rejected.json())
    assert section.class_sessions.count() == 1

    restored = auth_client.patch(
        url, {"service_status": "available"}, content_type="application/json"
    )
    assert restored.status_code == 200
    assert create_class_session(**payload, day_of_week=2).classroom_id == classroom.pk


@pytest.mark.parametrize("status", ["unavailable", "maintenance"])
def test_new_default_assignments_rejected_existing_reference_can_be_kept(room_context, status):
    classroom, section, _ = room_context
    cycle = section.academic_cycle
    cycle.status = AcademicCycle.CycleStatus.DRAFT
    cycle.save(update_fields=["status"])
    section.default_classroom = classroom
    section.save(update_fields=["default_classroom"])
    update_classroom(classroom=classroom, service_status=status)

    update_section(section=section, name="Conservada", default_classroom=classroom)
    section.refresh_from_db()
    assert section.default_classroom_id == classroom.pk
    with pytest.raises(DomainError, match="servicio"):
        create_section(
            academic_cycle=cycle,
            grade=section.grade,
            shift=section.shift,
            name="Nueva",
            default_classroom=classroom,
        )
    other = SectionFactory(academic_cycle=cycle, shift=section.shift)
    with pytest.raises(DomainError, match="servicio"):
        update_section(section=other, default_classroom=classroom)
    other.refresh_from_db()
    assert other.default_classroom_id is None


def test_invalid_status_rejected_by_service_and_api(auth_client, room_context):
    classroom, _, _ = room_context
    with pytest.raises(DomainError):
        update_classroom(classroom=classroom, service_status="invalid")
    response = auth_client.patch(
        reverse("classroom-detail", args=[classroom.public_id]),
        {"service_status": "invalid"},
        content_type="application/json",
    )
    assert response.status_code == 400
    classroom.refresh_from_db()
    assert classroom.service_status == "available"


def test_unauthenticated_status_change_is_rejected(client, room_context):
    classroom, _, _ = room_context
    response = client.patch(
        reverse("classroom-detail", args=[classroom.public_id]),
        {"service_status": "maintenance"},
        content_type="application/json",
    )
    assert response.status_code == 403
    classroom.refresh_from_db()
    assert classroom.service_status == "available"
    assert not AuditEvent.objects.filter(action="academics.classroom.updated").exists()


def test_foreign_classroom_status_cannot_be_changed(auth_client, institution):
    classroom = ClassroomFactory(campus=CampusFactory())
    response = auth_client.patch(
        reverse("classroom-detail", args=[classroom.public_id]),
        {"service_status": "maintenance"},
        content_type="application/json",
    )
    assert response.status_code == 404
    classroom.refresh_from_db()
    assert classroom.service_status == "available"


def test_inactive_classroom_cannot_receive_new_sessions(room_context):
    classroom, _, payload = room_context
    classroom.is_active = False
    classroom.save(update_fields=["is_active"])
    with pytest.raises(DomainError, match="inactivo"):
        create_class_session(**payload, day_of_week=1)


def test_legacy_create_defaults_to_available_and_unrelated_patch_keeps_status(
    auth_client, institution
):
    campus = CampusFactory(institution=institution)
    created = auth_client.post(
        reverse("classroom-list-create"),
        {"campus_id": str(campus.public_id), "name": "Aula demo", "code": "DEMO"},
        content_type="application/json",
    )
    assert created.status_code == 201
    assert created.json()["service_status"] == "available"
    url = reverse("classroom-detail", args=[created.json()["public_id"]])
    auth_client.patch(url, {"service_status": "maintenance"}, content_type="application/json")
    response = auth_client.patch(url, {"name": "Aula renombrada"}, content_type="application/json")
    assert response.status_code == 200
    assert response.json()["service_status"] == "maintenance"
