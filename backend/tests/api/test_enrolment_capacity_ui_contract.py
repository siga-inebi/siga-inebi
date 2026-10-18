from datetime import date

import pytest
from django.urls import reverse

from apps.enrolments.models import Enrolment
from apps.enrolments.services import create_enrolment
from tests.factories.academic import SectionFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def occupancy(client, section):
    response = client.get(
        reverse("section-occupancy-list"),
        {
            "academic_cycle_id": str(section.academic_cycle.public_id),
            "section_id": str(section.public_id),
        },
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
    return response.json()["results"][0]


def test_selected_section_contract_distinguishes_available_full_and_withdrawn(auth_client):
    section = SectionFactory(capacity=1)
    SectionFactory()  # el panel no debe recibir otro catálogo completo
    assert occupancy(auth_client, section)["available_seats"] == 1
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    full = occupancy(auth_client, section)
    assert full["capacity"] == full["occupied_seats"] == 1
    assert full["available_seats"] == 0
    enrolment.status = "withdrawn"
    enrolment.save()
    released = occupancy(auth_client, section)
    assert released["occupied_seats"] == 0
    assert released["available_seats"] == 1


def test_zero_capacity_means_uncapped_not_full(auth_client):
    section = SectionFactory(capacity=0)
    for _ in range(2):
        create_enrolment(
            student=StudentFactory(),
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            section=section,
        )
    data = occupancy(auth_client, section)
    assert data["capacity"] == 0
    assert data["occupied_seats"] == 2
    assert data["available_seats"] is None


def test_a_prior_available_seat_does_not_bypass_write_capacity_guard(auth_client):
    section = SectionFactory(capacity=1)
    assert occupancy(auth_client, section)["available_seats"] == 1
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    permission = PermissionFactory(codename="enrollment_create")
    assignment = RoleAssignmentFactory(
        user=auth_client.user, role=RoleFactory(permissions=[permission])
    )
    ScopeGrantFactory(assignment=assignment, section=section)
    candidate = StudentFactory()
    before = Enrolment.objects.count()
    response = auth_client.post(
        reverse("matriculation-create"),
        {
            "student_id": str(candidate.public_id),
            "academic_cycle_id": str(section.academic_cycle.public_id),
            "grade_id": str(section.grade.public_id),
            "shift_id": str(section.shift.public_id),
            "section_id": str(section.public_id),
            "effective_on": date.today().isoformat(),
        },
        content_type="application/json",
    )
    assert response.status_code == 400
    assert Enrolment.objects.count() == before
    assert not Enrolment.objects.filter(student=candidate).exists()
    assert occupancy(auth_client, section)["available_seats"] == 0
