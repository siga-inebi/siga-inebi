from datetime import date

import pytest
from django.urls import reverse

from apps.audit.models import AuditEvent
from tests.factories.academic import SectionFactory
from tests.factories.identity import PermissionFactory, RoleAssignmentFactory, RoleFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def _grant_enrolment_creation(user):
    permission = PermissionFactory(codename="enrollment_create")
    return RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))


def _payload(section, student):
    return {
        "student_id": str(student.public_id),
        "academic_cycle_id": str(section.academic_cycle.public_id),
        "grade_id": str(section.grade.public_id),
        "section_id": str(section.public_id),
        "effective_on": "2026-02-01",
        "ends_on": "2026-10-30",
    }


def test_create_enrolment_returns_public_references_and_audits(auth_client):
    section = SectionFactory()
    student = StudentFactory()
    _grant_enrolment_creation(auth_client.user)

    response = auth_client.post(
        reverse("enrolment-list-create"),
        _payload(section, student),
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["student_id"] == str(student.public_id)
    assert body["academic_cycle_id"] == str(section.academic_cycle.public_id)
    assert body["grade_id"] == str(section.grade.public_id)
    assert body["section_id"] == str(section.public_id)
    assert body["effective_on"] == "2026-02-01"
    assert body["ends_on"] == "2026-10-30"
    assert AuditEvent.objects.filter(action="enrolments.enrolment.created").exists()


def test_create_enrolment_requires_domain_permission(auth_client):
    section = SectionFactory()
    response = auth_client.post(
        reverse("enrolment-list-create"),
        _payload(section, StudentFactory()),
        content_type="application/json",
    )

    assert response.status_code == 403


def test_create_enrolment_rejects_invalid_vigency_dates(auth_client):
    section = SectionFactory()
    _grant_enrolment_creation(auth_client.user)
    payload = _payload(section, StudentFactory())
    payload["ends_on"] = date(2026, 1, 31).isoformat()

    response = auth_client.post(
        reverse("enrolment-list-create"), payload, content_type="application/json"
    )

    assert response.status_code == 400
    assert "end date cannot precede" in response.json()["error"]["detail"]
