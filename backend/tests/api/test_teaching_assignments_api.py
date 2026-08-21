from datetime import date

import pytest
from django.urls import reverse

from apps.academics.models import AcademicCycle
from apps.academics.services import create_teaching_assignment
from tests.factories.academic import AcademicCycleFactory, SectionFactory, SubjectFactory
from tests.factories.identity import (
    PermissionFactory,
    RoleAssignmentFactory,
    RoleFactory,
    ScopeGrantFactory,
)
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def _assignment_context(institution):
    cycle = AcademicCycleFactory(
        institution=institution,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 12, 31),
    )
    return (
        cycle,
        SectionFactory(academic_cycle=cycle),
        SubjectFactory(institution=institution),
        TeacherFactory(),
    )


def _grant_assignment_scope(user, institution):
    permission = PermissionFactory(codename="scope_assign")
    assignment = RoleAssignmentFactory(user=user, role=RoleFactory(permissions=[permission]))
    return ScopeGrantFactory(assignment=assignment, institution=institution)


def test_create_reassign_and_filter_teaching_assignment_history(auth_client, institution):
    cycle, section, subject, first_teacher = _assignment_context(institution)
    second_teacher = TeacherFactory()
    _grant_assignment_scope(auth_client.user, institution)
    create_response = auth_client.post(
        reverse("teaching-assignment-list-create"),
        {
            "academic_cycle_id": str(cycle.public_id),
            "section_id": str(section.public_id),
            "subject_id": str(subject.public_id),
            "teacher_id": str(first_teacher.public_id),
        },
        content_type="application/json",
    )

    assert create_response.status_code == 201
    current = create_response.json()
    assert current["starts_on"] == "2026-01-01"
    assert current["ends_on"] is None
    assert current["teacher_id"] == str(first_teacher.public_id)

    reassign_response = auth_client.post(
        reverse("teaching-assignment-reassign", args=[current["public_id"]]),
        {"teacher_id": str(second_teacher.public_id), "ends_on": "2026-06-30"},
        content_type="application/json",
    )

    assert reassign_response.status_code == 201
    assert reassign_response.json()["starts_on"] == "2026-07-01"
    assert reassign_response.json()["teacher_id"] == str(second_teacher.public_id)

    first_history = auth_client.get(
        reverse("teaching-assignment-history"),
        {"teacher_id": str(first_teacher.public_id), "academic_cycle_id": str(cycle.public_id)},
    )
    assert first_history.status_code == 200
    assert len(first_history.json()["results"]) == 1
    assert first_history.json()["results"][0]["ends_on"] == "2026-06-30"


def test_history_keeps_a_teacher_trajectory_across_cycles(auth_client, institution):
    first_cycle, first_section, first_subject, teacher = _assignment_context(institution)
    _grant_assignment_scope(auth_client.user, institution)
    second_cycle = AcademicCycleFactory(
        institution=institution,
        starts_on=date(2027, 1, 1),
        ends_on=date(2027, 12, 31),
        status="draft",
    )
    second_section = SectionFactory(academic_cycle=second_cycle)
    second_subject = SubjectFactory(institution=institution)
    for cycle, section, subject in [
        (first_cycle, first_section, first_subject),
        (second_cycle, second_section, second_subject),
    ]:
        response = auth_client.post(
            reverse("teaching-assignment-list-create"),
            {
                "academic_cycle_id": str(cycle.public_id),
                "section_id": str(section.public_id),
                "subject_id": str(subject.public_id),
                "teacher_id": str(teacher.public_id),
            },
            content_type="application/json",
        )
        assert response.status_code == 201

    trajectory = auth_client.get(
        reverse("teaching-assignment-history"), {"teacher_id": str(teacher.public_id)}
    )
    only_first_cycle = auth_client.get(
        reverse("teaching-assignment-history"),
        {"teacher_id": str(teacher.public_id), "academic_cycle_id": str(first_cycle.public_id)},
    )

    assert len(trajectory.json()["results"]) == 2
    assert len(only_first_cycle.json()["results"]) == 1


def test_create_teaching_assignment_returns_validation_error_for_mismatched_section(
    auth_client, institution
):
    cycle, _, subject, teacher = _assignment_context(institution)
    foreign_section = SectionFactory()
    _grant_assignment_scope(auth_client.user, institution)

    response = auth_client.post(
        reverse("teaching-assignment-list-create"),
        {
            "academic_cycle_id": str(cycle.public_id),
            "section_id": str(foreign_section.public_id),
            "subject_id": str(subject.public_id),
            "teacher_id": str(teacher.public_id),
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "seccion debe pertenecer" in response.json()["error"]["detail"]


def test_teaching_assignment_endpoints_require_matching_institution_scope(auth_client, institution):
    cycle, section, subject, teacher = _assignment_context(institution)
    successor_teacher = TeacherFactory()
    assignment = create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
    )
    payload = {
        "academic_cycle_id": str(cycle.public_id),
        "section_id": str(section.public_id),
        "subject_id": str(subject.public_id),
        "teacher_id": str(teacher.public_id),
    }

    assert (
        auth_client.post(
            reverse("teaching-assignment-list-create"), payload, content_type="application/json"
        ).status_code
        == 403
    )
    assert (
        auth_client.post(
            reverse("teaching-assignment-reassign", args=[assignment.public_id]),
            {"teacher_id": str(successor_teacher.public_id), "ends_on": "2026-06-30"},
            content_type="application/json",
        ).status_code
        == 403
    )
    assert auth_client.get(reverse("teaching-assignment-history")).status_code == 403

    _grant_assignment_scope(auth_client.user, AcademicCycleFactory().institution)

    assert (
        auth_client.post(
            reverse("teaching-assignment-list-create"), payload, content_type="application/json"
        ).status_code
        == 403
    )
    assert (
        auth_client.post(
            reverse("teaching-assignment-reassign", args=[assignment.public_id]),
            {"teacher_id": str(successor_teacher.public_id), "ends_on": "2026-06-30"},
            content_type="application/json",
        ).status_code
        == 403
    )
    assert auth_client.get(reverse("teaching-assignment-history")).status_code == 403


def test_closed_cycle_rejects_teaching_assignment_api_writes(auth_client, institution):
    cycle, section, subject, teacher = _assignment_context(institution)
    assignment = create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
    )
    cycle.status = AcademicCycle.CycleStatus.CLOSED
    cycle.save(update_fields=["status", "updated_at"])
    _grant_assignment_scope(auth_client.user, institution)

    create_response = auth_client.post(
        reverse("teaching-assignment-list-create"),
        {
            "academic_cycle_id": str(cycle.public_id),
            "section_id": str(section.public_id),
            "subject_id": str(subject.public_id),
            "teacher_id": str(TeacherFactory().public_id),
        },
        content_type="application/json",
    )
    reassign_response = auth_client.post(
        reverse("teaching-assignment-reassign", args=[assignment.public_id]),
        {"teacher_id": str(TeacherFactory().public_id), "ends_on": "2026-06-30"},
        content_type="application/json",
    )

    assert create_response.status_code == 400
    assert reassign_response.status_code == 400
    assert "ciclo escolar cerrado" in create_response.json()["error"]["detail"]
    assert "ciclo escolar cerrado" in reassign_response.json()["error"]["detail"]

    history_response = auth_client.get(
        reverse("teaching-assignment-history"),
        {"academic_cycle_id": str(cycle.public_id)},
    )
    assert history_response.status_code == 200
    assert len(history_response.json()["results"]) == 1
