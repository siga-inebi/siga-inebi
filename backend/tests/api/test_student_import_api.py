"""
Importacion CSV de estudiantes, todo o nada (vista previa y confirmacion).

``GET students/import/template/``, ``POST students/import/preview/`` y
``POST students/import/confirm/``. El permiso es el del alta individual.
"""

import hashlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.people.models import Person
from apps.students.imports import MAX_IMPORT_ROWS, TEMPLATE_COLUMNS
from apps.students.models import Student
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.people import PersonFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]

HEADER = ",".join(TEMPLATE_COLUMNS)


@pytest.fixture
def importer(auth_client):
    assignment = RoleAssignmentFactory(
        user=auth_client.user,
        role=RoleFactory(permissions=[PermissionFactory(codename="student_edit_basic")]),
    )
    ScopeGrantFactory(assignment=assignment, module_key="students")
    return auth_client


def _csv(*lines, header=HEADER):
    return ("﻿" + "\r\n".join([header, *lines]) + "\r\n").encode("utf-8")


def _upload(raw, name="estudiantes.csv"):
    return SimpleUploadedFile(name, raw, content_type="text/csv")


def _preview(client, raw):
    return client.post(reverse("student-import-preview"), {"file": _upload(raw)})


def _confirm(client, raw, digest=None):
    digest = digest if digest is not None else hashlib.sha256(raw).hexdigest()
    return client.post(
        reverse("student-import-confirm"), {"file": _upload(raw), "file_sha256": digest}
    )


VALID = (
    "Ana,Pérez,1234567890101,2012-03-15,F,ana@example.test,55501234,",
    "Luis,García,,2011-07-01,masculino,,,",
)


def test_template_is_utf8_with_bom_and_headers_only(importer):
    response = importer.get(reverse("student-import-template"))

    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv; charset=utf-8"
    assert "attachment" in response["Content-Disposition"]
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert response.content.decode("utf-8-sig") == (
        "nombres,apellidos,cui,fecha_nacimiento,sexo,correo,telefono,codigo_estudiante\r\n"
    )


def test_import_requires_the_student_creation_permission(auth_client):
    raw = _csv(*VALID)

    assert auth_client.get(reverse("student-import-template")).status_code == 403
    assert _preview(auth_client, raw).status_code == 403
    assert _confirm(auth_client, raw).status_code == 403
    assert not Student.objects.exists()


def test_preview_reports_every_row_and_persists_nothing(importer):
    StudentFactory(student_code="EST-EXISTE")
    raw = _csv(
        *VALID,
        "Eva,Ruiz,1234567890101,2012-01-01,F,,,",
        "Sol,Mena,,15/03/2012,F,,,",
        "Leo,Paz,,,,,,EST-EXISTE",
        ",Sin Nombre,,,,,,",
        "Ada,Luna,123,,X,no-es-correo,,",
    )
    people_before = Person.objects.count()
    students_before = Student.objects.count()

    response = _preview(importer, raw)

    assert response.status_code == 200
    body = response.json()
    assert body["file_sha256"] == hashlib.sha256(raw).hexdigest()
    assert body["summary"] == {"total": 7, "ready": 2, "errors": 5}
    rows = {row["line"]: row for row in body["rows"]}
    assert rows[2]["status"] == "ready" and rows[2]["errors"] == []
    assert rows[2]["data"]["nombres"] == "Ana"
    assert set(rows[2]["data"]) == set(TEMPLATE_COLUMNS)
    assert rows[3]["status"] == "ready"
    assert any("se repite en la fila 2" in error for error in rows[4]["errors"])
    assert any("AAAA-MM-DD" in error for error in rows[5]["errors"])
    assert any("EST-EXISTE" in error for error in rows[6]["errors"])
    assert any("nombres es obligatorio" in error for error in rows[7]["errors"])
    assert len(rows[8]["errors"]) == 3  # CUI, sexo y correo
    assert Person.objects.count() == people_before
    assert Student.objects.count() == students_before
    event = AuditEvent.objects.get(action="students.import.previewed")
    assert event.context["total"] == 7
    assert event.context["errors"] == 5


def test_preview_rejects_cui_of_existing_people(importer):
    student = StudentFactory()
    student.person.cui = "1111111111111"
    student.person.save()
    PersonFactory(cui="2222222222222")
    raw = _csv("Uno,Dos,1111111111111,,,,,", "Tres,Cuatro,2222222222222,,,,,")

    rows = _preview(importer, raw).json()["rows"]

    assert rows[0]["errors"] == ["El CUI ya pertenece a un estudiante registrado."]
    assert "Convertir persona" in rows[1]["errors"][0]


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        (_csv(*VALID, header="nombres,apellidos,cui"), "Faltan columnas"),
        (_csv(*VALID, header=HEADER + ",extra"), "no reconocidas"),
        (b"", "vac"),
        (_csv(), "no contiene filas"),
        ("nombres;apellidos".encode("utf-16"), "UTF-8"),
        (_csv(*(["Ana,Pérez,,,,,,"] * (MAX_IMPORT_ROWS + 1))), "500 filas"),
    ],
)
def test_structural_problems_reject_the_whole_file(importer, raw, message):
    response = _preview(importer, raw)

    assert response.status_code == 400
    assert message in str(response.json()["error"]["detail"])


def test_confirm_with_a_different_file_is_a_conflict(importer):
    raw = _csv(*VALID)

    response = _confirm(importer, raw, digest=hashlib.sha256(b"otro archivo").hexdigest())

    assert response.status_code == 409
    assert "vista previa" in response.json()["detail"]
    assert not Student.objects.exists()
    assert AuditEvent.objects.get(action="students.import.rejected").context["reason"] == (
        "file_changed"
    )


def test_confirm_with_any_failing_row_inserts_nothing(importer):
    raw = _csv(*VALID, "Sol,Mena,,2012-13-40,F,,,")
    people_before = Person.objects.count()

    response = _confirm(importer, raw)

    assert response.status_code == 422
    body = response.json()
    assert body["summary"] == {"total": 3, "ready": 2, "errors": 1}
    assert body["rows"][2]["status"] == "error"
    assert not Student.objects.exists()
    assert Person.objects.count() == people_before
    assert not AuditEvent.objects.filter(action="students.student.created").exists()
    event = AuditEvent.objects.get(action="students.import.rejected")
    assert event.context["reason"] == "row_errors"
    assert event.context["errors"] == 1


def test_confirm_creates_every_student(importer):
    year = timezone.localdate().year
    # Fila 2 sin codigo y fila 3 con el que la serie generaria primero: los
    # codigos explicitos se reservan antes, asi que las dos entran.
    raw = _csv(
        "Ana,Pérez,1234567890101,2012-03-15,femenino,ana@example.test,55501234,",
        f"Luis,García,,,M,,,EST-{year}-0001",
    )

    preview = _preview(importer, raw)
    response = _confirm(importer, raw, digest=preview.json()["file_sha256"])

    assert preview.json()["summary"]["errors"] == 0
    assert response.status_code == 201
    body = response.json()
    assert body["created"] == 2
    by_name = {student["full_name"]: student for student in body["students"]}
    assert by_name["Luis García"]["student_code"] == f"EST-{year}-0001"
    assert by_name["Ana Pérez"]["student_code"] == f"EST-{year}-0002"
    ana = Student.objects.get(public_id=by_name["Ana Pérez"]["public_id"])
    assert ana.status == Student.StudentStatus.PRE_ENROLLED
    assert ana.person.cui == "1234567890101"
    assert ana.person.sex == Person.Sex.FEMALE
    assert str(ana.person.birth_date) == "2012-03-15"
    event = AuditEvent.objects.get(action="students.import.processed")
    assert event.context["created"] == 2
    assert AuditEvent.objects.filter(action="students.student.created").count() == 2
