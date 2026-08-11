"""
RF-JOR-001 — contrato del endpoint de parametros de jornada.
"""

import pytest
from django.urls import reverse

from tests.factories.academic import AcademicCycleFactory, ShiftFactory
from tests.factories.identity import PermissionFactory, RoleAssignmentFactory, RoleFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

CONFIGURE_PERMISSION = "attendance_jornada_configure"


def _grant(user, codename):
    permission = PermissionFactory(codename=codename)
    RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))


def _payload(shift, cycle):
    return {
        "shift_id": str(shift.public_id),
        "academic_cycle_id": str(cycle.public_id),
        "entry_limit_time": "07:00:00",
        "tolerance_minutes": 10,
        "closing_time": "13:00:00",
        "duplicate_suppression_minutes": 5,
        "school_days": [1, 2, 3, 4, 5],
        "effective_from": str(cycle.starts_on),
    }


def test_create_jornada_parameters_requires_permission(auth_client):
    shift = ShiftFactory()
    cycle = AcademicCycleFactory(institution=shift.institution)

    response = auth_client.post(
        reverse("attendance-jornada-parameters-list"),
        _payload(shift, cycle),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_jornada_parameters_with_permission(auth_client):
    _grant(auth_client.user, CONFIGURE_PERMISSION)
    shift = ShiftFactory()
    cycle = AcademicCycleFactory(institution=shift.institution)

    response = auth_client.post(
        reverse("attendance-jornada-parameters-list"),
        _payload(shift, cycle),
        content_type="application/json",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["entry_limit_time"] == "07:00:00"
    assert data["shift_id"] == str(shift.public_id)


def test_create_jornada_parameters_with_unknown_shift_is_rejected(auth_client):
    _grant(auth_client.user, CONFIGURE_PERMISSION)
    shift = ShiftFactory()
    cycle = AcademicCycleFactory(institution=shift.institution)
    payload = _payload(shift, cycle)
    payload["shift_id"] = "00000000-0000-0000-0000-000000000000"

    response = auth_client.post(
        reverse("attendance-jornada-parameters-list"),
        payload,
        content_type="application/json",
    )

    assert response.status_code == 400


def test_list_jornada_parameters_requires_permission(auth_client):
    response = auth_client.get(reverse("attendance-jornada-parameters-list"))

    assert response.status_code == 403


def test_unauthenticated_request_is_rejected(client):
    response = client.get(reverse("attendance-jornada-parameters-list"))

    assert response.status_code == 403
