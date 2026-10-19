from datetime import date, timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.enrolments.models import Enrolment, StudentMovement
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


def grant(user, *, scoped=True):
    role = RoleFactory(
        permissions=[
            PermissionFactory(codename="enrollment_update"),
            PermissionFactory(codename="student_view_basic"),
        ]
    )
    assignment = RoleAssignmentFactory(user=user, role=role, identity_scope=False)
    if scoped:
        ScopeGrantFactory(assignment=assignment, module_key="students")


def context():
    today = timezone.localdate()
    cycle = AcademicCycleFactory(
        year=today.year, starts_on=date(today.year, 1, 1), ends_on=date(today.year, 12, 31)
    )
    source = SectionFactory(academic_cycle=cycle)
    target = SectionFactory(academic_cycle=cycle, grade=source.grade)
    student = StudentFactory()
    enrolment = create_enrolment(
        student=student,
        academic_cycle=cycle,
        grade=source.grade,
        section=source,
        effective_on=today,
    )
    return today, student, enrolment, target


def incoming_payload(student, target, effective_on):
    return {
        "student_id": str(student.public_id),
        "academic_cycle_id": str(target.academic_cycle.public_id),
        "grade_id": str(target.grade.public_id),
        "shift_id": str(target.shift.public_id),
        "section_id": str(target.public_id),
        "effective_on": effective_on.isoformat(),
    }


def test_transfer_round_trip_uses_search_and_distinct_immutable_movements(auth_client):
    today, student, source, target = context()
    grant(auth_client.user)
    out = auth_client.post(
        reverse("student-transfer-out", args=[source.public_id]),
        {"effective_on": today.isoformat(), "reason": "Synthetic transfer"},
        content_type="application/json",
    )
    assert out.status_code == 201
    assert out.json()["movement_type"] == "transfer_out"
    assert out.json()["source_enrolment_id"] == str(source.public_id)
    student.refresh_from_db()
    assert student.status == "transferred"
    assert (
        auth_client.get(reverse("active-enrolment-list"), {"student_id": student.public_id}).json()[
            "count"
        ]
        == 0
    )
    # The existing picker must still find this institutional record after leaving.
    search = auth_client.get(reverse("student-list"), {"search": student.student_code})
    assert search.status_code == 200
    assert search.json()["results"][0]["public_id"] == str(student.public_id)
    incoming = auth_client.post(
        reverse("student-transfer-in"),
        incoming_payload(student, target, today),
        content_type="application/json",
    )
    assert incoming.status_code == 201
    assert incoming.json()["movement_type"] == "transfer_in"
    assert incoming.json()["source_enrolment_id"] is None
    assert incoming.json()["target_enrolment_id"] != str(source.public_id)
    source.refresh_from_db()
    student.refresh_from_db()
    assert source.status == "completed"
    assert student.status == "active"
    assert Enrolment.objects.filter(student=student, status="active").count() == 1
    history = auth_client.get(
        reverse("student-movement-list"), {"student_id": student.public_id}
    ).json()
    assert history["count"] == 2
    assert {row["movement_type"] for row in history["results"]} == {"transfer_in", "transfer_out"}
    assert AuditEvent.objects.filter(
        actor=auth_client.user, action="enrolments.student.transferred_in"
    ).exists()
    assert AuditEvent.objects.filter(
        actor=auth_client.user, action="enrolments.student.transferred_out"
    ).exists()


@pytest.mark.parametrize("direction", ["in", "out"])
def test_future_transfer_rejected_without_partial_writes(auth_client, direction):
    today, student, source, target = context()
    grant(auth_client.user)
    future = today + timedelta(days=1)
    if direction == "in":
        url = reverse("student-transfer-in")
        payload = incoming_payload(student, target, future)
    else:
        url = reverse("student-transfer-out", args=[source.public_id])
        payload = {"effective_on": future.isoformat(), "reason": "Synthetic future transfer"}
    response = auth_client.post(url, payload, content_type="application/json")
    assert response.status_code == 400
    assert "fecha futura" in response.json()["error"]["detail"]
    assert not StudentMovement.objects.filter(student=student).exists()
    source.refresh_from_db()
    student.refresh_from_db()
    assert source.status == "active"
    assert student.status == "active"
    assert Enrolment.objects.filter(student=student).count() == 1


def test_transfer_in_denies_missing_permission_or_scope_without_writes(auth_client):
    today, _student, _source, target = context()
    student = StudentFactory(status="transferred")
    url = reverse("student-transfer-in")
    payload = incoming_payload(student, target, today)
    assert auth_client.post(url, payload, content_type="application/json").status_code == 403
    grant(auth_client.user, scoped=False)
    assert auth_client.post(url, payload, content_type="application/json").status_code == 403
    assert not Enrolment.objects.filter(student=student).exists()
    assert not StudentMovement.objects.filter(student=student).exists()
