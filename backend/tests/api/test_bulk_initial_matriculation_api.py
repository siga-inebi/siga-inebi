from datetime import date
from uuid import uuid4

import pytest
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.enrolments.models import Enrolment
from apps.enrolments.services import create_enrolment
from tests.factories.academic import SectionFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def grant(user, codename="enrollment_create", **scope):
    assignment = RoleAssignmentFactory(
        user=user, role=RoleFactory(permissions=[PermissionFactory(codename=codename)])
    )
    if scope:
        ScopeGrantFactory(assignment=assignment, **scope)


def send(client, section, students, preview=True, **extra):
    return client.post(
        reverse("bulk-matriculation-create"),
        {
            "section_id": str(section.public_id),
            "effective_on": "2026-02-01",
            "student_ids": [str(getattr(s, "public_id", s)) for s in students],
            "preview": preview,
            **extra,
        },
        content_type="application/json",
    )


def test_preview_checks_cumulative_capacity_and_rolls_back_every_write(auth_client):
    section = SectionFactory(capacity=1)
    students = StudentFactory.create_batch(2, status="pre_enrolled")
    grant(auth_client.user, section=section)
    response = send(auth_client, section, students)
    assert response.status_code == 200
    assert [r["status"] for r in response.json()["results"]] == ["ready", "error"]
    assert Enrolment.objects.count() == 0
    assert not AuditEvent.objects.filter(action="enrolments.student.matriculated").exists()
    assert all(
        StudentFactory._meta.model.objects.get(pk=s.pk).status == "pre_enrolled" for s in students
    )


def test_partial_confirmation_and_retry_preserve_existing_enrolments(auth_client):
    section = SectionFactory(capacity=1)
    students = StudentFactory.create_batch(2)
    grant(auth_client.user, section=section)
    first = send(auth_client, section, students, preview=False).json()
    assert [r["status"] for r in first["results"]] == ["created", "error"]
    second = send(auth_client, section, students, preview=False).json()
    assert [r["status"] for r in second["results"]] == ["existing", "error"]
    assert second["results"][0]["enrolment_id"] == first["results"][0]["enrolment_id"]
    assert Enrolment.objects.count() == 1
    assert AuditEvent.objects.filter(action="enrolments.student.matriculated").count() == 1


def test_per_student_error_does_not_abort_others(auth_client):
    section = SectionFactory()
    inactive = StudentFactory(is_active=False)
    eligible = StudentFactory()
    grant(auth_client.user, section=section)
    response = send(auth_client, section, [uuid4(), inactive, eligible], preview=False)
    assert response.status_code == 200
    assert [r["status"] for r in response.json()["results"]] == ["error", "error", "created"]
    assert Enrolment.objects.get().student == eligible


@pytest.mark.parametrize("problem", ["duplicate", "empty", "too_many", "bad_uuid"])
def test_invalid_batch_is_rejected_before_writes(auth_client, problem):
    section = SectionFactory()
    student = StudentFactory()
    grant(auth_client.user, section=section)
    ids = {
        "duplicate": [student, student],
        "empty": [],
        "too_many": [uuid4() for _ in range(101)],
        "bad_uuid": ["bad"],
    }[problem]
    assert send(auth_client, section, ids, preview=False).status_code == 400
    assert not Enrolment.objects.exists()


@pytest.mark.parametrize("access", ["anonymous", "no_permission", "no_scope", "other_section"])
def test_scope_denial_precedes_batch_writes(client, auth_client, access):
    section = SectionFactory()
    student = StudentFactory()
    if access == "no_scope":
        grant(auth_client.user)
    elif access == "other_section":
        grant(auth_client.user, section=SectionFactory())
    actor = client if access == "anonymous" else auth_client
    assert send(actor, section, [student], preview=False).status_code == 403
    assert not Enrolment.objects.exists()


def test_retry_does_not_accept_a_different_effective_date(auth_client):
    section = SectionFactory()
    student = StudentFactory()
    grant(auth_client.user, section=section)
    assert send(auth_client, section, [student], preview=False).json()["succeeded"] == 1
    result = send(auth_client, section, [student], preview=False, effective_on="2026-03-01").json()
    assert result["results"][0]["status"] == "error"
    assert Enrolment.objects.get().effective_on == date(2026, 2, 1)


def test_candidate_search_is_authorized_filtered_before_pagination(auth_client):
    section = SectionFactory()
    grant(auth_client.user, section=section)
    grant(auth_client.user, "student_view_basic", module_key="students")
    matches = StudentFactory.create_batch(26)
    for student in matches:
        student.person.first_name = "Candidato"
        student.person.save()
    occupied = StudentFactory()
    occupied.person.first_name = "Candidato"
    occupied.person.save()
    create_enrolment(
        student=occupied,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    StudentFactory.create_batch(26)
    seen = []
    for page in [1, 2]:
        response = auth_client.get(
            reverse("initial-matriculation-candidates"),
            {
                "section_id": str(section.public_id),
                "search": "Candidato",
                "page": page,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 26
        assert all(set(r) == {"public_id", "full_name", "student_code"} for r in data["results"])
        seen.extend(r["public_id"] for r in data["results"])
    assert len(set(seen)) == 26


def test_candidate_visibility_does_not_expand_student_scope(auth_client):
    section = SectionFactory()
    allowed, hidden = StudentFactory.create_batch(2)
    grant(auth_client.user, section=section)
    grant(auth_client.user, "student_view_basic", student=allowed)
    response = auth_client.get(
        reverse("initial-matriculation-candidates"), {"section_id": str(section.public_id)}
    )
    assert response.status_code == 200
    assert [r["public_id"] for r in response.json()["results"]] == [str(allowed.public_id)]
    assert str(hidden.public_id) not in response.content.decode()


def test_confirmation_rechecks_capacity_after_successful_preview(auth_client):
    section = SectionFactory(capacity=1)
    selected, other = StudentFactory.create_batch(2)
    grant(auth_client.user, section=section)
    assert send(auth_client, section, [selected]).json()["results"][0]["status"] == "ready"
    create_enrolment(
        student=other, academic_cycle=section.academic_cycle, grade=section.grade, section=section
    )
    assert send(auth_client, section, [selected], preview=False).json()["failed"] == 1
    assert Enrolment.objects.get().student == other


def test_active_enrolment_in_another_cycle_is_not_closed(auth_client):
    target, source = SectionFactory.create_batch(2)
    student = StudentFactory()
    previous = create_enrolment(
        student=student, academic_cycle=source.academic_cycle, grade=source.grade, section=source
    )
    grant(auth_client.user, section=target)
    assert send(auth_client, target, [student], preview=False).json()["failed"] == 1
    previous.refresh_from_db()
    assert previous.status == "active" and previous.ends_on is None
    assert student.enrolments.count() == 1


def test_unexpected_failure_rolls_back_the_whole_request(auth_client, monkeypatch):
    from apps.enrolments import bulk_initial

    section = SectionFactory()
    students = StudentFactory.create_batch(2)
    grant(auth_client.user, section=section)
    original = bulk_initial.matriculate_student

    def fail_second(**kwargs):
        if kwargs["student"].pk == students[1].pk:
            raise RuntimeError("simulated storage failure")
        return original(**kwargs)

    monkeypatch.setattr(bulk_initial, "matriculate_student", fail_second)
    with pytest.raises(RuntimeError):
        send(auth_client, section, students, preview=False)
    assert not Enrolment.objects.exists()
    assert not AuditEvent.objects.filter(action="enrolments.student.matriculated").exists()


def test_candidates_require_student_read_permission_and_destination_scope(auth_client):
    section = SectionFactory()
    grant(auth_client.user, section=section)
    assert (
        auth_client.get(
            reverse("initial-matriculation-candidates"),
            {
                "section_id": str(section.public_id),
            },
        ).status_code
        == 403
    )
