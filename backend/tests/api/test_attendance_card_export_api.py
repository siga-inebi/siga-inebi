"""
RF-CRE-002 — reimpresion del QR con permiso propio y exportacion de carnes.

- ``POST attendance/credentials/qr/``: QR de la credencial vigente, auditado
  sin el token.
- ``POST attendance/credentials/export/preview/`` y ``.../export/``: PDF, PNG
  o ZIP para 1 a 100 estudiantes; emite las que faltan solo con el permiso de
  emision y omite el resto con su motivo.
"""

import base64
import importlib
import io
import json
import zipfile
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.contrib.auth.models import Permission
from django.db import connection
from django.urls import reverse
from PIL import Image

from apps.attendance import services
from apps.attendance.models import StudentCredential
from apps.audit.models import AuditEvent
from apps.common.qr import generate_qr_png
from apps.enrolments.services import create_enrolment
from tests.factories.academic import AcademicCycleFactory, SectionFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

PRINT = "attendance_credential_print"
ISSUE = "attendance_credential_issue"


def _enrol(student):
    cycle = AcademicCycleFactory()
    section = SectionFactory(academic_cycle=cycle)
    create_enrolment(
        student=student, academic_cycle=cycle, grade=section.offering.grade, section=section
    )
    return section


def _grant(user, codename, *students):
    assignment = RoleAssignmentFactory(
        user=user, role=RoleFactory(permissions=[PermissionFactory(codename=codename)])
    )
    for student in students:
        ScopeGrantFactory(assignment=assignment, student=student)


def _enrolled_student(*, credential=False):
    student = StudentFactory()
    _enrol(student)
    issued = services.issue_credential(student=student) if credential else None
    return student, issued


def _post(client, name, payload):
    return client.post(reverse(name), payload, content_type="application/json")


def _ids(*students):
    return [str(student.public_id) for student in students]


# --------------------------------------------------------------------------- #
# QR
# --------------------------------------------------------------------------- #


def test_qr_requires_the_print_permission_even_with_the_issue_one(auth_client):
    student, _credential = _enrolled_student(credential=True)
    _grant(auth_client.user, ISSUE, student)

    response = _post(auth_client, "attendance-credential-qr", {"student_id": _ids(student)[0]})

    assert response.status_code == 403
    assert not AuditEvent.objects.filter(action="attendance.credential.qr_revealed").exists()


def test_qr_of_a_student_outside_the_print_scope_is_forbidden(auth_client):
    student, _credential = _enrolled_student(credential=True)
    other, _ = _enrolled_student()
    _grant(auth_client.user, PRINT, other)

    response = _post(auth_client, "attendance-credential-qr", {"student_id": _ids(student)[0]})

    assert response.status_code == 403


def test_qr_returns_the_active_credential_qr_and_audits_without_the_token(auth_client):
    student, credential = _enrolled_student(credential=True)
    _grant(auth_client.user, PRINT, student)

    response = _post(auth_client, "attendance-credential-qr", {"student_id": _ids(student)[0]})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"qr_code"}
    assert base64.b64decode(body["qr_code"]) == generate_qr_png(data=credential.opaque_identifier)
    event = AuditEvent.objects.get(action="attendance.credential.qr_revealed")
    assert event.actor == auth_client.user
    assert event.context["student_id"] == str(student.public_id)
    assert credential.opaque_identifier not in json.dumps(event.context)
    assert credential.opaque_identifier not in event.resource_identifier


def test_qr_can_be_revealed_again_without_revoking(auth_client):
    student, _credential = _enrolled_student(credential=True)
    _grant(auth_client.user, PRINT, student)

    for _ in range(2):
        response = _post(auth_client, "attendance-credential-qr", {"student_id": _ids(student)[0]})
        assert response.status_code == 200
    assert AuditEvent.objects.filter(action="attendance.credential.qr_revealed").count() == 2
    assert StudentCredential.objects.filter(student=student).count() == 1


def test_qr_without_an_active_credential_is_a_bad_request(auth_client):
    student, _ = _enrolled_student()
    _grant(auth_client.user, PRINT, student)

    response = _post(auth_client, "attendance-credential-qr", {"student_id": _ids(student)[0]})

    assert response.status_code == 400
    assert "credencial vigente" in response.json()["error"]["detail"]


# --------------------------------------------------------------------------- #
# exportacion
# --------------------------------------------------------------------------- #


def _mixed_batch(user):
    """ready, to_issue, sin inscripcion y fuera de alcance, en ese orden."""
    ready, _ = _enrolled_student(credential=True)
    missing, _ = _enrolled_student()
    unenrolled = StudentFactory()
    outsider, _ = _enrolled_student(credential=True)
    _grant(user, PRINT, ready, missing, unenrolled)
    _grant(user, ISSUE, ready, missing, unenrolled)
    return ready, missing, unenrolled, outsider


def test_export_preview_requires_the_print_permission(auth_client):
    student, _credential = _enrolled_student(credential=True)
    _grant(auth_client.user, ISSUE, student)

    response = _post(
        auth_client,
        "attendance-credential-export-preview",
        {"student_ids": _ids(student), "format": "pdf"},
    )

    assert response.status_code == 403


def test_export_preview_classifies_rows_and_issues_nothing(auth_client):
    ready, missing, unenrolled, outsider = _mixed_batch(auth_client.user)
    credentials_before = StudentCredential.objects.count()
    issued_events_before = AuditEvent.objects.filter(action="attendance.credential.issued").count()

    response = _post(
        auth_client,
        "attendance-credential-export-preview",
        {"student_ids": _ids(ready, missing, unenrolled, outsider), "format": "pdf"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["summary"] == {"total": 4, "ready": 1, "to_issue": 1, "skipped": 2}
    rows = body["rows"]
    assert [row["status"] for row in rows] == ["ready", "to_issue", "skipped", "skipped"]
    assert rows[0] == {
        "student_id": str(ready.public_id),
        "full_name": f"{ready.person.first_name} {ready.person.last_name}",
        "student_code": ready.student_code,
        "status": "ready",
        "reason": None,
    }
    assert "inscripción activa" in rows[2]["reason"]
    # Fuera de alcance: ni nombre ni codigo.
    assert rows[3]["full_name"] == "" and rows[3]["student_code"] == ""
    assert rows[3]["reason"]
    assert StudentCredential.objects.count() == credentials_before
    assert not StudentCredential.objects.filter(student=missing).exists()
    issued_events = AuditEvent.objects.filter(action="attendance.credential.issued").count()
    assert issued_events == issued_events_before


def test_export_issues_missing_cards_skips_the_rest_and_audits_without_tokens(auth_client):
    ready, missing, unenrolled, outsider = _mixed_batch(auth_client.user)

    response = _post(
        auth_client,
        "attendance-credential-export",
        {"student_ids": _ids(ready, missing, unenrolled, outsider), "format": "pdf"},
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Content-Disposition"].startswith('attachment; filename="carnes-')
    assert response["Content-Disposition"].endswith('.pdf"')
    assert response["Cache-Control"] == "no-store"
    assert response.content.startswith(b"%PDF-")
    issued = StudentCredential.objects.get(student=missing)
    assert issued.status == StudentCredential.Status.ACTIVE
    assert not StudentCredential.objects.filter(student=unenrolled).exists()

    event = AuditEvent.objects.get(action="attendance.credential.exported")
    assert event.context["count"] == 2
    assert event.context["issued"] == 1
    assert event.context["skipped"] == 2
    assert event.context["student_ids"] == _ids(ready, missing)
    serialized = json.dumps(event.context)
    for credential in StudentCredential.objects.all():
        assert credential.opaque_identifier not in serialized


def test_export_without_issue_permission_skips_students_without_a_card(auth_client):
    student, _ = _enrolled_student()
    _grant(auth_client.user, PRINT, student)

    preview = _post(
        auth_client,
        "attendance-credential-export-preview",
        {"student_ids": _ids(student), "format": "pdf"},
    )
    response = _post(
        auth_client,
        "attendance-credential-export",
        {"student_ids": _ids(student), "format": "pdf"},
    )

    row = preview.json()["rows"][0]
    assert row["status"] == "skipped"
    assert "permiso para emitir" in row["reason"]
    # Nada exportable: 400 con el sobre de error habitual y nada emitido.
    assert response.status_code == 400
    assert "exportable" in response.json()["error"]["detail"]
    assert not StudentCredential.objects.filter(student=student).exists()
    assert not AuditEvent.objects.filter(action="attendance.credential.exported").exists()


def test_png_export_returns_one_card_named_after_the_student(auth_client):
    student, _credential = _enrolled_student(credential=True)
    student.person.first_name = "Ána"
    student.person.last_name = "Pérez"
    student.person.save()
    _grant(auth_client.user, PRINT, student)

    response = _post(
        auth_client,
        "attendance-credential-export",
        {"student_ids": _ids(student), "format": "png"},
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "image/png"
    assert (
        response["Content-Disposition"]
        == f'attachment; filename="{student.student_code}_Ana-Perez.png"'
    )
    image = Image.open(io.BytesIO(response.content))
    assert image.size == (1134, 638)
    assert image.mode == "RGBA"


def test_png_export_with_two_students_is_a_bad_request(auth_client):
    first, _ = _enrolled_student(credential=True)
    second, _ = _enrolled_student(credential=True)
    _grant(auth_client.user, PRINT, first, second)

    for name in ("attendance-credential-export-preview", "attendance-credential-export"):
        response = _post(auth_client, name, {"student_ids": _ids(first, second), "format": "png"})
        assert response.status_code == 400


def test_zip_export_contains_one_png_per_card(auth_client):
    first, _ = _enrolled_student(credential=True)
    second, _ = _enrolled_student(credential=True)
    _grant(auth_client.user, PRINT, first, second)

    response = _post(
        auth_client,
        "attendance-credential-export",
        {"student_ids": _ids(first, second), "format": "zip"},
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/zip"
    assert response["Content-Disposition"].endswith('.zip"')
    names = zipfile.ZipFile(io.BytesIO(response.content)).namelist()
    assert len(names) == 2
    assert all(name.endswith(".png") for name in names)
    assert names[0].startswith(f"{first.student_code}_")


def test_export_accepts_at_most_one_hundred_distinct_students(auth_client):
    student, _ = _enrolled_student(credential=True)
    _grant(auth_client.user, PRINT, student)
    too_many = [str(StudentFactory.build().public_id) for _ in range(101)]

    over = _post(
        auth_client,
        "attendance-credential-export-preview",
        {"student_ids": too_many, "format": "zip"},
    )
    repeated = _post(
        auth_client,
        "attendance-credential-export-preview",
        {"student_ids": _ids(student, student), "format": "zip"},
    )
    empty = _post(
        auth_client, "attendance-credential-export-preview", {"student_ids": [], "format": "zip"}
    )

    assert over.status_code == 400
    assert repeated.status_code == 400
    assert empty.status_code == 400


def test_print_permission_migration_is_idempotent_and_grants_no_role():
    migration = importlib.import_module(
        "apps.identity.migrations.0019_seed_credential_print_permission"
    )
    role = RoleFactory()
    editor = SimpleNamespace(connection=connection)

    migration.seed_permission(apps, editor)
    migration.seed_permission(apps, editor)

    permission = Permission.objects.get(
        content_type__app_label="identity",
        content_type__model="role",
        codename=PRINT,
    )
    assert permission.name == "Reimprimir y exportar carnés"
    assert not role.permissions.exists()
