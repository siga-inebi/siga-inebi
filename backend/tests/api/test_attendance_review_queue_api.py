"""
#631 (AS2–AS5) — contratos de lectura de asistencia para la interfaz.

- ``GET /attendance/justifications/`` y ``GET …/justifications/{id}/``.
- ``GET /attendance/permits/`` y ``GET …/permits/{id}/``; nombres aditivos en
  las respuestas de alta y resolución.
- ``GET /attendance/credentials/status/``.
- ``GET /attendance/manual-registration-reasons/`` solo con vigentes.
- ``GET /attendance/capture-batches/current/`` expone el vencimiento.
"""

from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.attendance.models import AttendancePermit, Justification, JustificationAttachment
from tests.factories.attendance import (
    AttendancePermitFactory,
    CaptureBatchFactory,
    JustificationFactory,
    ManualRegistrationReasonFactory,
    StudentCredentialFactory,
)
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.people import PersonFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

JUSTIFICATION_REQUEST = "attendance_justification_request"
JUSTIFICATION_RESOLVE = "attendance_justification_resolve"
PERMIT_REQUEST = "attendance_permit_request"
PERMIT_RESOLVE = "attendance_permit_resolve"
CREDENTIAL_ISSUE = "attendance_credential_issue"


def _grant(user, codename, *students):
    permission = PermissionFactory(codename=codename)
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    for student in students:
        ScopeGrantFactory(assignment=assignment, student=student)


# --------------------------------------------------------------------------- #
# Justificaciones
# --------------------------------------------------------------------------- #


def test_justification_list_row_carries_names_and_labels(auth_client):
    student = StudentFactory(
        student_code="STU-9001", person=PersonFactory(first_name="Ana", last_name="Pérez")
    )
    _grant(auth_client.user, JUSTIFICATION_RESOLVE, student)
    justification = JustificationFactory(student=student)

    response = auth_client.get(reverse("attendance-justification-submit"))

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    row = body["results"][0]
    assert row["public_id"] == str(justification.public_id)
    assert row["student"] == {
        "public_id": str(student.public_id),
        "student_code": "STU-9001",
        "full_name": "Ana Pérez",
    }
    assert row["status"] == "pending"
    assert row["status_display"] == "Pendiente"
    assert row["situation_type_display"] == "Inasistencia"
    assert row["reason_catalog"] is None
    assert row["has_attachment"] is False
    assert row["submitted_by"] == {
        "public_id": str(justification.submitted_by.public_id),
        "name": str(justification.submitted_by.person),
    }
    assert row["submitted_at"]
    assert row["resolved_by"] is None
    assert row["resolved_at"] is None


def test_justification_list_query_count_does_not_grow_with_rows(auth_client):
    students = [StudentFactory() for _ in range(6)]
    _grant(auth_client.user, JUSTIFICATION_RESOLVE, *students)
    url = reverse("attendance-justification-submit")
    JustificationFactory(student=students[0])

    with CaptureQueriesContext(connection) as one_row:
        assert auth_client.get(url).status_code == 200

    for student in students[1:]:
        justification = JustificationFactory(student=student)
        JustificationAttachment.objects.create(
            justification=justification,
            uploaded_by=justification.submitted_by,
            filename="constancia.pdf",
            storage_key=f"justifications/{justification.public_id}.pdf",
            content_type="application/pdf",
            size_bytes=10,
            checksum="0" * 64,
        )
    with CaptureQueriesContext(connection) as six_rows:
        response = auth_client.get(url)

    assert response.json()["count"] == 6
    assert sum(row["has_attachment"] for row in response.json()["results"]) == 5
    assert len(six_rows) == len(one_row)


def test_justification_list_filters_by_status_and_search(auth_client):
    student = StudentFactory(person=PersonFactory(first_name="Luis", last_name="Ochoa"))
    other = StudentFactory()
    _grant(auth_client.user, JUSTIFICATION_RESOLVE, student, other)
    target = JustificationFactory(student=student)
    JustificationFactory(student=student, status=Justification.Status.APPROVED)
    JustificationFactory(student=other)

    response = auth_client.get(
        reverse("attendance-justification-submit"), {"status": "pending", "search": "ochoa"}
    )

    assert [row["public_id"] for row in response.json()["results"]] == [str(target.public_id)]


def test_justification_list_rejects_an_inverted_date_range(auth_client):
    _grant(auth_client.user, JUSTIFICATION_RESOLVE)
    today = timezone.localdate()

    response = auth_client.get(
        reverse("attendance-justification-submit"),
        {"date_from": str(today), "date_to": str(today - timedelta(days=1))},
    )

    assert response.status_code == 400


def test_justification_list_rejects_an_unknown_status(auth_client):
    _grant(auth_client.user, JUSTIFICATION_RESOLVE)

    response = auth_client.get(reverse("attendance-justification-submit"), {"status": "nope"})

    assert response.status_code == 400


def test_justification_detail_returns_the_visible_row(auth_client):
    _grant(auth_client.user, JUSTIFICATION_REQUEST)
    own = JustificationFactory(submitted_by=auth_client.user)

    response = auth_client.get(reverse("attendance-justification-detail", args=[own.public_id]))

    assert response.status_code == 200
    assert response.json()["public_id"] == str(own.public_id)
    assert response.json()["student"]["public_id"] == str(own.student.public_id)


def test_justification_submit_response_keeps_ids_and_adds_names(auth_client):
    student = StudentFactory()
    _grant(auth_client.user, JUSTIFICATION_REQUEST, student)

    response = auth_client.post(
        reverse("attendance-justification-submit"),
        {
            "student_id": str(student.public_id),
            "absence_date": str(timezone.localdate() - timedelta(days=1)),
            "reason": "Cita medica",
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["student_id"] == str(student.public_id)
    assert body["submitted_by_id"] == auth_client.user.pk
    assert body["student"]["public_id"] == str(student.public_id)
    assert body["submitted_by"]["public_id"] == str(auth_client.user.public_id)
    assert body["has_attachment"] is False


def test_justification_resolve_response_names_the_resolver(auth_client):
    student = StudentFactory()
    _grant(auth_client.user, JUSTIFICATION_RESOLVE, student)
    justification = JustificationFactory(student=student)

    response = auth_client.post(
        reverse("attendance-justification-resolve", args=[justification.public_id]),
        {"approved": True, "comment": ""},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["resolved_by"] == {
        "public_id": str(auth_client.user.public_id),
        "name": str(auth_client.user.person),
    }
    assert response.json()["status_display"] == "Aprobada"


# --------------------------------------------------------------------------- #
# Permisos de salida anticipada o ingreso tardio
# --------------------------------------------------------------------------- #


def test_permit_list_row_carries_names_and_labels(auth_client):
    student = StudentFactory(person=PersonFactory(first_name="Eva", last_name="Ruiz"))
    _grant(auth_client.user, PERMIT_RESOLVE, student)
    permit = AttendancePermitFactory(student=student)

    response = auth_client.get(reverse("attendance-permit-submit"))

    assert response.status_code == 200
    row = response.json()["results"][0]
    assert row["public_id"] == str(permit.public_id)
    assert row["student"]["full_name"] == "Eva Ruiz"
    assert row["permit_type_display"] == "Salida anticipada"
    assert row["status_display"] == "Pendiente"
    assert row["submitted_by"]["public_id"] == str(permit.submitted_by.public_id)
    assert row["resolved_by"] is None


def test_permit_list_query_count_does_not_grow_with_rows(auth_client):
    students = [StudentFactory() for _ in range(5)]
    _grant(auth_client.user, PERMIT_RESOLVE, *students)
    url = reverse("attendance-permit-submit")
    AttendancePermitFactory(student=students[0])

    with CaptureQueriesContext(connection) as one_row:
        auth_client.get(url)
    for student in students[1:]:
        AttendancePermitFactory(student=student, status=AttendancePermit.Status.APPROVED)
    with CaptureQueriesContext(connection) as five_rows:
        response = auth_client.get(url)

    assert response.json()["count"] == 5
    assert len(five_rows) == len(one_row)


def test_permit_list_filters_by_type(auth_client):
    _grant(auth_client.user, PERMIT_REQUEST)
    AttendancePermitFactory(submitted_by=auth_client.user)
    late = AttendancePermitFactory(
        submitted_by=auth_client.user, permit_type=AttendancePermit.PermitType.LATE_ARRIVAL
    )

    response = auth_client.get(reverse("attendance-permit-submit"), {"permit_type": "late_arrival"})

    assert [row["public_id"] for row in response.json()["results"]] == [str(late.public_id)]


def test_permit_detail_returns_the_visible_row(auth_client):
    _grant(auth_client.user, PERMIT_REQUEST)
    own = AttendancePermitFactory(submitted_by=auth_client.user)

    response = auth_client.get(reverse("attendance-permit-detail", args=[own.public_id]))

    assert response.status_code == 200
    assert response.json()["student"]["public_id"] == str(own.student.public_id)


def test_permit_submit_and_resolve_responses_add_names(auth_client):
    student = StudentFactory()
    _grant(auth_client.user, PERMIT_REQUEST, student)
    _grant(auth_client.user, PERMIT_RESOLVE, student)

    created = auth_client.post(
        reverse("attendance-permit-submit"),
        {
            "student_id": str(student.public_id),
            "permit_type": "early_exit",
            "permit_date": str(timezone.localdate()),
            "scheduled_time": "13:00:00",
            "reason": "Cita medica",
        },
        content_type="application/json",
    )
    resolved = auth_client.post(
        reverse("attendance-permit-resolve", args=[created.json()["public_id"]]),
        {"approved": True, "comment": ""},
        content_type="application/json",
    )

    assert created.status_code == 201
    assert created.json()["submitted_by_id"] == auth_client.user.pk
    assert created.json()["student"]["public_id"] == str(student.public_id)
    assert created.json()["submitted_by"]["public_id"] == str(auth_client.user.public_id)
    assert resolved.status_code == 200
    assert resolved.json()["resolved_by"]["public_id"] == str(auth_client.user.public_id)
    assert resolved.json()["status_display"] == "Aprobado"


# --------------------------------------------------------------------------- #
# Estado de la credencial
# --------------------------------------------------------------------------- #


def _credential_status(client, student):
    return client.get(reverse("attendance-credential-status"), {"student_id": student.public_id})


def test_credential_status_without_credential_is_none(auth_client):
    student = StudentFactory()
    _grant(auth_client.user, CREDENTIAL_ISSUE, student)

    response = _credential_status(auth_client, student)

    assert response.status_code == 200
    assert response.json() == {
        "student_id": str(student.public_id),
        "status": "none",
        "public_id": None,
        "issued_at": None,
        "revoked_at": None,
        "revocation_reason": None,
    }


def test_credential_status_never_returns_the_token_or_the_qr(auth_client):
    credential = StudentCredentialFactory()
    _grant(auth_client.user, CREDENTIAL_ISSUE, credential.student)

    response = _credential_status(auth_client, credential.student)

    body = response.json()
    assert body["status"] == "active"
    assert body["public_id"] == str(credential.public_id)
    assert "opaque_identifier" not in body
    assert "qr_code" not in body
    assert credential.opaque_identifier not in response.content.decode()


def test_credential_status_after_revocation_reports_reason_and_date(auth_client):
    credential = StudentCredentialFactory()
    _grant(auth_client.user, CREDENTIAL_ISSUE, credential.student)
    auth_client.post(
        reverse("attendance-credential-revoke"),
        {"student_id": str(credential.student.public_id), "reason": "Extravío"},
        content_type="application/json",
    )

    body = _credential_status(auth_client, credential.student).json()

    assert body["status"] == "revoked"
    assert body["revocation_reason"] == "Extravío"
    assert body["revoked_at"] is not None


def test_credential_status_requires_a_student_id(auth_client):
    _grant(auth_client.user, CREDENTIAL_ISSUE)

    assert auth_client.get(reverse("attendance-credential-status")).status_code == 400


# --------------------------------------------------------------------------- #
# Motivos de registro manual y turno de captura
# --------------------------------------------------------------------------- #


def test_manual_registration_reasons_hide_retired_ones_by_default(auth_client):
    active = ManualRegistrationReasonFactory()
    retired = ManualRegistrationReasonFactory(is_active=False)
    url = reverse("attendance-manual-registration-reason-list")

    default = auth_client.get(url).json()["results"]
    retired_only = auth_client.get(url, {"is_active": "false"}).json()["results"]

    assert [row["public_id"] for row in default] == [str(active.public_id)]
    assert [row["public_id"] for row in retired_only] == [str(retired.public_id)]


def test_current_capture_batch_exposes_its_expiry(auth_client):
    _grant(auth_client.user, "attendance_scan")
    expires_at = timezone.now() + timedelta(hours=2)
    CaptureBatchFactory(operator=auth_client.user, expires_at=expires_at)

    response = auth_client.get(reverse("attendance-capture-batch-current"))

    assert response.status_code == 200
    assert response.json()["capture_batch"]["expires_at"] is not None
