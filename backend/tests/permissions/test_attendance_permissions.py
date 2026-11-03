"""
RNF-PRI-003 — el rechazo por autorizacion tampoco deja nada en el dispositivo.
#631 (AS2–AS4) — bandejas de justificaciones y permisos y estado de credencial:
denegacion por defecto, alcance del revisor y solo lo propio para el solicitante.

Una respuesta 403 no trae datos del estudiante, pero si trae el identificador
que el operador consulto; el navegador no debe guardar ni esa respuesta ni la
exitosa, sin importar quien la pida.
"""

from urllib.parse import urlencode

import pytest
from django.urls import reverse
from django.utils import timezone

from tests.factories.academic import ShiftFactory
from tests.factories.attendance import (
    AttendancePermitFactory,
    JornadaParametersFactory,
    JustificationFactory,
)
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


# --------------------------------------------------------------------------- #
# #631 (AS2–AS4) — bandejas de justificaciones y permisos, estado de credencial
# --------------------------------------------------------------------------- #


def _grant(user, codename, *students):
    permission = PermissionFactory(codename=codename)
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    for student in students:
        ScopeGrantFactory(assignment=assignment, student=student)


@pytest.mark.parametrize(
    "url_name", ["attendance-justification-submit", "attendance-permit-submit"]
)
def test_review_queues_deny_without_request_or_resolve_permission(auth_client, url_name):
    response = auth_client.get(reverse(url_name))

    assert response.status_code == 403


def test_review_queues_require_authentication(client):
    assert client.get(reverse("attendance-justification-submit")).status_code == 403
    assert client.get(reverse("attendance-permit-submit")).status_code == 403


def test_justification_requester_does_not_see_other_submitters_rows(auth_client):
    _grant(auth_client.user, "attendance_justification_request")
    own = JustificationFactory(submitted_by=auth_client.user)
    other = JustificationFactory(student=own.student)

    listed = auth_client.get(reverse("attendance-justification-submit")).json()["results"]
    detail = auth_client.get(reverse("attendance-justification-detail", args=[other.public_id]))

    assert [row["public_id"] for row in listed] == [str(own.public_id)]
    assert detail.status_code == 404


def test_justification_reviewer_does_not_see_students_outside_scope(auth_client):
    in_scope = StudentFactory()
    _grant(auth_client.user, "attendance_justification_resolve", in_scope)
    visible = JustificationFactory(student=in_scope)
    outside = JustificationFactory()

    listed = auth_client.get(reverse("attendance-justification-submit")).json()["results"]
    detail = auth_client.get(reverse("attendance-justification-detail", args=[outside.public_id]))

    assert [row["public_id"] for row in listed] == [str(visible.public_id)]
    assert detail.status_code == 404


def test_justification_detail_denies_without_any_justification_permission(auth_client):
    justification = JustificationFactory(submitted_by=auth_client.user)

    response = auth_client.get(
        reverse("attendance-justification-detail", args=[justification.public_id])
    )

    assert response.status_code == 403


def test_permit_requester_does_not_see_other_requesters_rows(auth_client):
    _grant(auth_client.user, "attendance_permit_request")
    own = AttendancePermitFactory(submitted_by=auth_client.user)
    other = AttendancePermitFactory(student=own.student)

    listed = auth_client.get(reverse("attendance-permit-submit")).json()["results"]
    detail = auth_client.get(reverse("attendance-permit-detail", args=[other.public_id]))

    assert [row["public_id"] for row in listed] == [str(own.public_id)]
    assert detail.status_code == 404


def test_permit_reviewer_does_not_see_students_outside_scope(auth_client):
    in_scope = StudentFactory()
    _grant(auth_client.user, "attendance_permit_resolve", in_scope)
    visible = AttendancePermitFactory(student=in_scope)
    outside = AttendancePermitFactory()

    listed = auth_client.get(reverse("attendance-permit-submit")).json()["results"]
    detail = auth_client.get(reverse("attendance-permit-detail", args=[outside.public_id]))

    assert [row["public_id"] for row in listed] == [str(visible.public_id)]
    assert detail.status_code == 404


def test_credential_status_requires_issue_permission_with_student_scope(auth_client):
    student = StudentFactory()
    _grant(auth_client.user, "attendance_credential_issue", StudentFactory())

    response = auth_client.get(
        reverse("attendance-credential-status"), {"student_id": str(student.public_id)}
    )

    assert response.status_code == 403
    assert "status" not in response.json()


def test_credential_status_requires_authentication(client):
    response = client.get(
        reverse("attendance-credential-status"), {"student_id": str(StudentFactory().public_id)}
    )

    assert response.status_code == 403
