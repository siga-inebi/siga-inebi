"""
RF-JOR-007 — contrato de ``GET /api/v1/attendance/absence-notifications/``:
la cuenta de un encargado activo con relacion vigente consulta las
notificaciones de inasistencia de sus estudiantes; cualquier otra cuenta se
deniega por defecto (mismo patron que RF-JUS-006 y RF-HOR-010).
"""

import pytest
from django.urls import reverse

from apps.attendance import services
from apps.audit.models import AuditEvent
from apps.students.services import create_student_guardian_relation
from tests.factories.attendance import JornadaParametersFactory
from tests.factories.identity import UserFactory
from tests.factories.students import GuardianFactory, StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

URL_NAME = "attendance-absence-notification-list"


def _guardian_client(client):
    """A freshly provisioned guardian account: no roles, no scope grants."""
    guardian = GuardianFactory()
    user = UserFactory(person=guardian.person)
    client.force_login(user)
    return client, guardian


def _ward_with_notification(guardian, parameters):
    student = StudentFactory()
    create_student_guardian_relation(student=student, guardian=guardian, relationship_label="Madre")
    services.notify_absence(
        student=student, shift=parameters.shift, absence_date=parameters.effective_from
    )
    return student


def test_guardian_without_roles_lists_only_absence_notifications_of_current_wards(client):
    """
    RF-JOR-007: un encargado recien provisionado, sin roles ni asignaciones
    manuales, ve la notificacion de inasistencia de su estudiante y ninguna
    de estudiantes de otros encargados.
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


def test_non_guardian_staff_account_is_denied_and_audited(auth_client):
    """
    RF-JOR-007: una cuenta de personal sin relacion de encargado se deniega
    por defecto y la denegacion queda en la bitacora.
    """
    _ward_with_notification(GuardianFactory(), JornadaParametersFactory())

    response = auth_client.get(reverse(URL_NAME))

    assert response.status_code == 403
    assert AuditEvent.objects.filter(
        action="attendance.absence_notification.read_denied",
        actor=auth_client.user,
    ).exists()


def test_absence_notification_list_requires_authentication(client):
    """RF-JOR-007: sin autenticacion no hay acceso."""
    response = client.get(reverse(URL_NAME))

    assert response.status_code in (401, 403)
