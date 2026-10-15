"""
RF-JOR-007 — contrato de ``GET /api/v1/attendance/absence-notifications/``:
el encargado consulta las notificaciones de inasistencia de sus estudiantes
con asociacion vigente, con permiso atomico y denegacion por defecto.
"""

import pytest
from django.urls import reverse

from apps.attendance import services
from apps.students.services import create_student_guardian_relation
from tests.factories.attendance import JornadaParametersFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    UserFactory,
)
from tests.factories.students import GuardianFactory, StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

URL_NAME = "attendance-absence-notification-list"
VIEW_PERMISSION = "attendance_absence_notification_view"


def _guardian_client(client, *, with_permission=True):
    guardian = GuardianFactory()
    user = UserFactory(person=guardian.person)
    if with_permission:
        RoleAssignmentFactory(
            user=user,
            role=RoleFactory(permissions=[PermissionFactory(codename=VIEW_PERMISSION)]),
            identity_scope=False,
        )
    client.force_login(user)
    return client, guardian


def _ward_with_notification(guardian, parameters):
    student = StudentFactory()
    create_student_guardian_relation(student=student, guardian=guardian, relationship_label="Madre")
    services.notify_absence(
        student=student, shift=parameters.shift, absence_date=parameters.effective_from
    )
    return student


def test_guardian_lists_only_absence_notifications_of_current_wards(client):
    """
    RF-JOR-007: el encargado ve la notificacion de inasistencia de su
    estudiante y ninguna de estudiantes de otros encargados.
    """
    parameters = JornadaParametersFactory()
    client, guardian = _guardian_client(client)
    own_ward = _ward_with_notification(guardian, parameters)
    _ward_with_notification(GuardianFactory(), parameters)

    response = client.get(reverse(URL_NAME))

    assert response.status_code == 200
    results = response.json()["results"]
    assert [item["student_id"] for item in results] == [str(own_ward.public_id)]
    assert results[0]["absence_date"] == str(parameters.effective_from)
    assert results[0]["reason"] == "inasistencia"
    assert results[0]["is_superseded"] is False


def test_another_guardian_does_not_see_foreign_absence_notifications(client):
    """RF-JOR-007: otro encargado con sus propios estudiantes recibe una lista vacia."""
    parameters = JornadaParametersFactory()
    _ward_with_notification(GuardianFactory(), parameters)
    client, other_guardian = _guardian_client(client)
    create_student_guardian_relation(
        student=StudentFactory(), guardian=other_guardian, relationship_label="Padre"
    )

    response = client.get(reverse(URL_NAME))

    assert response.status_code == 200
    assert response.json()["results"] == []


def test_guardian_without_permission_is_denied(client):
    """RF-JOR-007: sin ``attendance_absence_notification_view`` se deniega por defecto."""
    parameters = JornadaParametersFactory()
    client, guardian = _guardian_client(client, with_permission=False)
    _ward_with_notification(guardian, parameters)

    response = client.get(reverse(URL_NAME))

    assert response.status_code == 403


def test_absence_notification_list_requires_authentication(client):
    """RF-JOR-007: sin autenticacion no hay acceso."""
    response = client.get(reverse(URL_NAME))

    assert response.status_code in (401, 403)
