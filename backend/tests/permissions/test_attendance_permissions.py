"""
RNF-PRI-003 — el rechazo por autorizacion tampoco deja nada en el dispositivo.

Una respuesta 403 no trae datos del estudiante, pero si trae el identificador
que el operador consulto; el navegador no debe guardar ni esa respuesta ni la
exitosa, sin importar quien la pida.
"""

from urllib.parse import urlencode

import pytest
from django.urls import reverse
from django.utils import timezone

from tests.factories.academic import ShiftFactory
from tests.factories.attendance import JornadaParametersFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.permissions, pytest.mark.django_db]


def _presence_url(shift, event_date=None):
    event_date = event_date or timezone.localdate()
    query = urlencode({"shift_id": str(shift.public_id), "event_date": str(event_date)})
    return f"{reverse('attendance-presence')}?{query}"


def test_unauthenticated_rejection_is_not_stored_on_the_operator_device(client):
    response = client.get(_presence_url(ShiftFactory()))

    assert response.status_code == 403
    assert response.headers["Cache-Control"] == "no-store"


def test_out_of_scope_rejection_is_not_stored_on_the_operator_device(auth_client):
    response = auth_client.get(_presence_url(ShiftFactory()))

    assert response.status_code == 403
    assert response.headers["Cache-Control"] == "no-store"


def test_authorized_response_is_not_stored_on_the_operator_device(auth_client):
    permission = PermissionFactory(codename="student_view_basic")
    assignment = RoleAssignmentFactory(
        user=auth_client.user, role=RoleFactory(permissions=[permission])
    )
    ScopeGrantFactory(assignment=assignment, student=StudentFactory())
    parameters = JornadaParametersFactory()

    response = auth_client.get(
        _presence_url(parameters.shift, event_date=parameters.academic_cycle.starts_on)
    )

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
