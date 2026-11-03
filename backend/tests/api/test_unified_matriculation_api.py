from datetime import date

import pytest
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.enrolments.models import Enrolment
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


def grant(user, **scope):
    assignment = RoleAssignmentFactory(
        user=user, role=RoleFactory(permissions=[PermissionFactory(codename="enrollment_create")])
    )
    if scope:
        ScopeGrantFactory(assignment=assignment, **scope)


def payload(student, section):
    return {
        "student_id": str(student.public_id),
        "academic_cycle_id": str(section.academic_cycle.public_id),
        "grade_id": str(section.grade.public_id),
        "shift_id": str(section.shift.public_id),
        "section_id": str(section.public_id),
        "effective_on": "2027-02-01",
    }


def prior(student, target, status="active"):
    cycle = AcademicCycleFactory(
        institution=target.academic_cycle.institution,
        year=2026,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 12, 31),
        status="draft",
    )
    section = SectionFactory(academic_cycle=cycle, grade=target.grade, shift=target.shift)
    enrolment = create_enrolment(
        student=student,
        academic_cycle=cycle,
        grade=section.grade,
        section=section,
        effective_on=date(2026, 2, 1),
    )
    enrolment.status = status
    enrolment.save(update_fields=["status"])
    return enrolment


@pytest.fixture
def target():
    return SectionFactory(
        academic_cycle=AcademicCycleFactory(
            year=2027,
            starts_on=date(2027, 1, 1),
            ends_on=date(2027, 12, 31),
            status="draft",
        )
    )


def post(client, data):
    return client.post(
        reverse("unified-matriculation-create"), data, content_type="application/json"
    )


def test_first_matriculation_activates_existing_student(auth_client, target):
    student = StudentFactory(status="pre_enrolled")
    grant(auth_client.user, section=target)
    response = post(auth_client, payload(student, target))
    assert response.status_code == 201
    assert response.json()["registration_mode"] == "matriculation"
    assert response.json()["student_id"] == str(student.public_id)
    assert response.json()["shift_id"] == str(target.shift.public_id)
    student.refresh_from_db()
    assert student.status == "active"
    assert student.enrolments.count() == 1
    assert AuditEvent.objects.filter(action="enrolments.student.matriculated").exists()


@pytest.mark.parametrize("previous_status", ["active", "completed", "withdrawn"])
def test_history_selects_reenrolment_and_preserves_audited_origin(
    auth_client, target, previous_status
):
    student = StudentFactory()
    source = prior(student, target, previous_status)
    grant(auth_client.user, section=target)
    response = post(auth_client, payload(student, target))
    assert response.status_code == 201
    assert response.json()["registration_mode"] == "reenrolment"
    source.refresh_from_db()
    assert source.status == ("completed" if previous_status == "active" else previous_status)
    assert student.enrolments.count() == 2
    assert AuditEvent.objects.filter(
        action="enrolments.student.reenrolled",
        context__previous_enrolment_id=source.pk,
    ).exists()


def test_cancelled_history_is_not_inherited(auth_client, target):
    student = StudentFactory()
    source = prior(student, target, "cancelled")
    grant(auth_client.user, section=target)
    response = post(auth_client, payload(student, target))
    assert response.status_code == 201
    assert response.json()["registration_mode"] == "matriculation"
    source.refresh_from_db()
    assert source.status == "cancelled"


@pytest.mark.parametrize("history", [False, True])
def test_repeat_same_cycle_is_rejected_without_writes(auth_client, target, history):
    student = StudentFactory()
    if history:
        prior(student, target, "completed")
    grant(auth_client.user, section=target)
    assert post(auth_client, payload(student, target)).status_code == 201
    count = student.enrolments.count()
    events = AuditEvent.objects.count()
    assert post(auth_client, payload(student, target)).status_code == 400
    assert student.enrolments.count() == count
    assert AuditEvent.objects.count() == events
    assert student.enrolments.filter(status="active").count() == 1


@pytest.mark.parametrize("failure", ["full", "closed", "inactive", "shift", "grade"])
def test_failed_reenrolment_rolls_back_prior_closure(auth_client, target, failure):
    student = StudentFactory()
    source = prior(student, target)
    grant(auth_client.user, section=target)
    data = payload(student, target)
    if failure == "full":
        target.capacity = 1
        target.save()
        create_enrolment(
            student=StudentFactory(),
            academic_cycle=target.academic_cycle,
            grade=target.grade,
            section=target,
            effective_on=date(2027, 1, 1),
        )
    elif failure == "closed":
        target.academic_cycle.status = "closed"
        target.academic_cycle.save()
    elif failure == "inactive":
        student.is_active = False
        student.save()
    else:
        other = SectionFactory()
        data[f"{failure}_id"] = str(getattr(other, failure).public_id)
    count = Enrolment.objects.count()
    events = AuditEvent.objects.count()
    assert post(auth_client, data).status_code == 400
    assert Enrolment.objects.count() == count
    assert AuditEvent.objects.count() == events
    source.refresh_from_db()
    assert source.status == "active"
    assert source.ends_on is None


@pytest.mark.parametrize("access", ["anonymous", "no_permission", "no_scope", "other_section"])
def test_deny_before_writing_or_resolving_history(client, auth_client, target, access):
    student = StudentFactory()
    source = prior(student, target)
    if access == "no_scope":
        grant(auth_client.user)
    elif access == "other_section":
        grant(auth_client.user, section=SectionFactory())
    response = post(client if access == "anonymous" else auth_client, payload(student, target))
    assert response.status_code == 403
    assert student.enrolments.count() == 1
    source.refresh_from_db()
    assert source.status == "active"
