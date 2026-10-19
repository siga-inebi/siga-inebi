from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.enrolments.models import Enrolment
from tests.factories.academic import SectionFactory
from tests.factories.attendance import AttendanceEventFactory
from tests.factories.documents import DocumentRecordFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.students import (
    StudentFactory,
    StudentGuardianRelationFactory,
    StudentHealthNoteFactory,
)

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def grant(user, student, codename="student_view_basic"):
    role = RoleFactory(permissions=[PermissionFactory(codename=codename)])
    ScopeGrantFactory(assignment=RoleAssignmentFactory(user=user, role=role), student=student)


def test_record_uuid_read_preserves_protected_person_fields(auth_client):
    student = StudentFactory()
    grant(auth_client.user, student)
    response = auth_client.get(
        reverse("student-record-detail", kwargs={"public_id": student.public_id})
    )
    assert response.status_code == 200
    assert response.json()["public_id"] == str(student.public_id)
    assert "cui" not in response.json()["person"]
    assert "birth_date" not in response.json()["person"]
    assert "health_notes" not in response.json()
    assert response.headers["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "endpoint,arg,permission",
    [
        ("student-record-detail", "public_id", "student_view_basic"),
        ("student-record-guardians", "public_id", "student_view_basic"),
        ("student-record-enrolments", "student_id", "student_view_basic"),
        ("student-document-record-list", "student_id", "document_read"),
    ],
)
def test_record_endpoints_deny_without_permission_or_scope(
    client, auth_client, endpoint, arg, permission
):
    student, other = StudentFactory.create_batch(2)
    url = reverse(endpoint, kwargs={arg: student.public_id})
    assert Client().get(url).status_code == 403
    assert auth_client.get(url).status_code == 403
    grant(auth_client.user, other, permission)
    assert auth_client.get(url).status_code in {403, 404}


@pytest.mark.parametrize("kind", ["guardians", "documents", "enrolments", "attendance", "health"])
def test_record_collections_filter_before_count_and_paginate(auth_client, kind):
    student, other = StudentFactory.create_batch(2)
    grant(auth_client.user, student)
    if kind == "guardians":
        StudentGuardianRelationFactory.create_batch(26, student=student, is_primary=False)
        StudentGuardianRelationFactory.create_batch(26, student=other, is_primary=False)
        url = reverse("student-record-guardians", kwargs={"public_id": student.public_id})
    elif kind == "documents":
        grant(auth_client.user, student, "document_read")
        DocumentRecordFactory.create_batch(26, student=student)
        DocumentRecordFactory.create_batch(26, student=other)
        url = reverse("student-document-record-list", kwargs={"student_id": student.public_id})
    elif kind == "health":
        grant(auth_client.user, student, "student_view_sensitive")
        StudentHealthNoteFactory.create_batch(26, student=student)
        StudentHealthNoteFactory.create_batch(26, student=other)
        url = reverse("student-health-note-list-create", kwargs={"public_id": student.public_id})
    elif kind == "attendance":
        AttendanceEventFactory.create_batch(26, student=student)
        AttendanceEventFactory.create_batch(26, student=other)
        url = reverse("attendance-event-list")
    else:
        for pupil in [student, other]:
            for _ in range(26):
                section = SectionFactory()
                Enrolment.objects.create(
                    student=pupil,
                    academic_cycle=section.academic_cycle,
                    grade=section.grade,
                    section=section,
                    status="completed",
                )
        url = reverse("student-record-enrolments", kwargs={"student_id": student.public_id})
    seen = []
    for page in [1, 2]:
        response = auth_client.get(url, {"page": page, "student_id": str(student.public_id)})
        assert response.status_code == 200
        assert response.json()["count"] == 26
        seen.extend(row.get("public_id", row.get("id")) for row in response.json()["results"])
    assert len(seen) == len(set(seen)) == 26


def test_enrolment_summary_includes_names_and_server_current_state(auth_client):
    student = StudentFactory()
    grant(auth_client.user, student)
    section = SectionFactory()
    Enrolment.objects.create(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        effective_on=timezone.localdate() - timedelta(days=1),
    )
    response = auth_client.get(
        reverse("student-record-enrolments", kwargs={"student_id": student.public_id})
    )
    row = response.json()["results"][0]
    assert row["cycle_name"] == section.academic_cycle.name
    assert row["section_name"] == section.name
    assert row["shift_name"] == section.shift.name
    assert row["is_current"] is True


def test_record_metadata_edits_persist_all_existing_person_fields(auth_client):
    student = StudentFactory()
    grant(auth_client.user, student)
    changes = {
        "sex": "female",
        "nationality": "Demo",
        "address": "Direccion demo",
        "department": "Departamento demo",
        "municipality": "Municipio demo",
    }
    response = auth_client.patch(
        reverse("person-detail", kwargs={"public_id": student.person.public_id}),
        changes,
        content_type="application/json",
    )
    assert response.status_code == 200
    record = auth_client.get(
        reverse("student-record-detail", kwargs={"public_id": student.public_id})
    ).json()
    assert all(record["person"][key] == value for key, value in changes.items())


def test_attendance_filter_rejects_malformed_uuid(auth_client):
    assert (
        auth_client.get(reverse("attendance-event-list"), {"student_id": "invalid"}).status_code
        == 400
    )


def test_health_is_not_exposed_with_basic_permission(auth_client):
    student = StudentFactory()
    grant(auth_client.user, student)
    note = StudentHealthNoteFactory(student=student, content="Contenido sintetico restringido")
    response = auth_client.get(
        reverse("student-health-note-list-create", kwargs={"public_id": student.public_id})
    )
    assert response.status_code == 403
    assert note.content not in response.content.decode()
    assert not AuditEvent.objects.filter(context__content=note.content).exists()
