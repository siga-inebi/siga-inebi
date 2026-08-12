import pytest
from django.urls import reverse

from apps.academics.models import AcademicCycle
from tests.factories.academic import AcademicCycleFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_create_academic_cycle_contract(auth_client, institution):
    response = auth_client.post(
        reverse("academic-cycle-list-create"),
        {
            "year": 2027,
            "name": "Ciclo 2027",
            "description": "Plan institucional",
            "starts_on": "2027-01-15",
            "ends_on": "2027-10-31",
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["status"] == AcademicCycle.CycleStatus.DRAFT
    assert response.json()["year"] == 2027
    assert response.json()["description"] == "Plan institucional"


def test_cycle_end_date_before_start_is_rejected(auth_client, institution):
    response = auth_client.post(
        reverse("academic-cycle-list-create"),
        {
            "year": 2027,
            "name": "Ciclo 2027",
            "starts_on": "2027-10-31",
            "ends_on": "2027-01-15",
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "cannot be before" in response.json()["error"]["detail"]


def test_activate_cycle_rejects_when_an_active_cycle_exists(auth_client, institution):
    AcademicCycleFactory(
        institution=institution,
        year=2026,
        status=AcademicCycle.CycleStatus.ACTIVE,
    )
    prepared = AcademicCycleFactory(
        institution=institution,
        year=2027,
        starts_on="2027-01-01",
        ends_on="2027-12-31",
        status=AcademicCycle.CycleStatus.DRAFT,
    )

    response = auth_client.post(reverse("academic-cycle-activate", args=[prepared.public_id]))

    assert response.status_code == 400
    assert "must be closed" in response.json()["error"]["detail"]


def test_cycle_endpoints_require_authentication(client, institution):
    assert client.get(reverse("academic-cycle-list-create")).status_code == 403
    response = client.post(
        reverse("academic-cycle-list-create"),
        {},
        content_type="application/json",
    )
    assert response.status_code == 403
