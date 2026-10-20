import pytest
from django.test import Client
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.enrolments.models import Enrolment
from apps.students.services import deactivate_student
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
    EmergencyContactFactory,
    StudentFactory,
    StudentGuardianRelationFactory,
    StudentHealthNoteFactory,
    StudentObservationFactory,
)

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def grant(user, student, *permissions):
    assignment = RoleAssignmentFactory(
        user=user,
        role=RoleFactory(permissions=[PermissionFactory(codename=code) for code in permissions]),
    )
    ScopeGrantFactory(assignment=assignment, student=student)


def dossier(student):
    return reverse("student-record-detail", kwargs={"public_id": student.public_id})


def test_deactivation_keeps_person_relations_academic_and_sensitive_history(auth_client):
    student = StudentFactory(status="active")
    person = student.person
    relation = StudentGuardianRelationFactory(student=student)
    section = SectionFactory()
    enrolment = Enrolment.objects.create(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    document = DocumentRecordFactory(student=student, enrolment=enrolment)
    records = [
        StudentHealthNoteFactory(student=student),
        StudentObservationFactory(student=student),
        EmergencyContactFactory(student=student),
        AttendanceEventFactory(student=student),
    ]
    grant(auth_client.user, student, "student_view_basic", "student_edit_basic")
    response = auth_client.delete(reverse("student-detail", args=[student.pk]))
    assert response.status_code == 204 and response.content == b""
    student.refresh_from_db()
    assert student.status == "inactive" and not student.is_active
    person.refresh_from_db()
    relation.refresh_from_db()
    enrolment.refresh_from_db()
    document.refresh_from_db()
    assert person.is_active and student.person_id == person.pk
    assert relation.ends_at is None and relation.is_active
    assert enrolment.status == "active" and enrolment.is_active
    assert document.student_id == student.pk and document.is_active
    for record in records:
        record.refresh_from_db()
        assert record.student_id == student.pk and record.is_active
    response = auth_client.get(dossier(student))
    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
    assert response.json()["actions"] == {"deactivate": False, "link_guardian": False}
    event = AuditEvent.objects.get(action="students.student.deactivated")
    assert event.actor == auth_client.user


def test_dossier_capabilities_do_not_audit_an_unattempted_write(auth_client):
    student = StudentFactory()
    grant(auth_client.user, student, "student_view_basic")
    response = auth_client.get(dossier(student))
    assert response.status_code == 200
    assert response.json()["actions"] == {"deactivate": False, "link_guardian": False}
    assert auth_client.head(dossier(student)).status_code == 200
    assert not AuditEvent.objects.filter(action="identity.authorization.denied").exists()
    grant(auth_client.user, student, "student_edit_basic")
    assert auth_client.get(dossier(student)).json()["actions"] == {
        "deactivate": True,
        "link_guardian": True,
    }


def test_delete_revalidates_permission_and_scope(auth_client):
    student, other = StudentFactory.create_batch(2)
    url = reverse("student-detail", args=[student.pk])
    assert Client().delete(url).status_code == 403
    grant(auth_client.user, student, "student_view_basic")
    assert auth_client.delete(url).status_code == 403
    grant(auth_client.user, other, "student_edit_basic")
    assert auth_client.delete(url).status_code == 404
    student.refresh_from_db()
    assert student.is_active
    assert not AuditEvent.objects.filter(action="students.student.deactivated").exists()


def test_student_deactivation_rolls_back_when_audit_fails(monkeypatch):
    student = StudentFactory(status="active")

    def fail(**kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("apps.students.services.record_event", fail)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        deactivate_student(student=student)
    student.refresh_from_db()
    assert student.is_active and student.status == "active"
