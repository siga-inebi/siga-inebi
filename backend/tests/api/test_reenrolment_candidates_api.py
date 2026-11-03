from datetime import date
from uuid import uuid4

import pytest
from django.test import Client
from django.urls import reverse

from apps.enrolments.models import Enrolment
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
        user=user,
        role=RoleFactory(permissions=[PermissionFactory(codename="enrollment_create")]),
        identity_scope=False,
    )
    if scope:
        ScopeGrantFactory(assignment=assignment, **scope)
    return assignment


def enrol(section, **kwargs):
    return Enrolment.objects.create(
        student=kwargs.pop("student", None) or StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        effective_on=date(2026, 1, 15),
        **kwargs,
    )


def test_candidates_deny_missing_session_permission_and_scope(auth_client):
    params = {"academic_cycle_id": uuid4()}
    url = reverse("reenrolment-candidate-list")
    assert Client().get(url, params).status_code == 403
    assert auth_client.get(url, params).status_code == 403
    grant(auth_client.user)
    assert auth_client.get(url, params).status_code == 403


@pytest.mark.parametrize("field", ["academic_cycle_id", "grade_id", "section_id"])
def test_filters_validate_public_uuids(auth_client, field):
    grant(auth_client.user, module_key="students")
    params = {"academic_cycle_id": uuid4(), field: "not-a-uuid"}
    assert auth_client.get(reverse("reenrolment-candidate-list"), params).status_code == 400
    assert auth_client.get(reverse("active-enrolment-list"), {field: "bad"}).status_code == 400


def test_candidates_require_cycle_and_bound_search(auth_client):
    grant(auth_client.user, module_key="students")
    url = reverse("reenrolment-candidate-list")
    assert auth_client.get(url).status_code == 400
    assert (
        auth_client.get(url, {"academic_cycle_id": uuid4(), "search": "x" * 151}).status_code == 400
    )


def test_candidates_filter_before_paging_and_include_completed_sources(auth_client):
    grant(auth_client.user, module_key="students")
    section = SectionFactory()
    # Outside the requested cycle: these must not consume any of its page slots.
    other = SectionFactory()
    for _ in range(26):
        enrol(other)
    expected = [enrol(section) for _ in range(26)]
    completed = enrol(section, status="completed")
    enrol(section, status="withdrawn")
    enrol(section, status="cancelled")
    enrol(section, is_active=False)
    enrol(section, student=StudentFactory(is_active=False))
    url = reverse("reenrolment-candidate-list")
    params = {"academic_cycle_id": section.academic_cycle.public_id}
    first = auth_client.get(url, params).json()
    second = auth_client.get(url, {**params, "page": 2}).json()
    assert first["count"] == second["count"] == 27
    assert len(first["results"]) == 25
    ids = [row["public_id"] for row in first["results"] + second["results"]]
    assert set(ids) == {str(row.public_id) for row in [*expected, completed]}
    assert len(ids) == len(set(ids))
    assert set(first["results"][0]) == {
        "public_id",
        "student_code",
        "first_name",
        "last_name",
        "grade_name",
        "section_name",
        "status",
    }


def test_candidates_apply_scope_name_code_and_academic_filters(auth_client):
    section = SectionFactory()
    allowed = enrol(
        section, student=StudentFactory(person__first_name="Ana", person__last_name="Lopez")
    )
    outside = enrol(SectionFactory())
    grant(auth_client.user, section=section)
    url = reverse("reenrolment-candidate-list")
    params = {"academic_cycle_id": section.academic_cycle.public_id}
    for search in ["ana LOPEZ", allowed.student.student_code]:
        body = auth_client.get(url, {**params, "search": search}).json()
        assert [row["public_id"] for row in body["results"]] == [str(allowed.public_id)]
    assert (
        auth_client.get(url, {"academic_cycle_id": outside.academic_cycle.public_id}).json()[
            "count"
        ]
        == 0
    )
    assert auth_client.get(url, {**params, "grade_id": uuid4()}).json()["count"] == 0
    assert auth_client.get(url, {**params, "section_id": uuid4()}).json()["count"] == 0
    assert (
        auth_client.get(
            url, {**params, "grade_id": section.grade.public_id, "section_id": section.public_id}
        ).json()["count"]
        == 1
    )
    assert auth_client.get(url, {**params, "search": "absent"}).json()["count"] == 0


def test_active_filters_combine_without_changing_active_only_contract(auth_client):
    section = SectionFactory()
    active = enrol(section)
    enrol(section, status="completed")
    enrol(SectionFactory())
    params = {
        "academic_cycle_id": section.academic_cycle.public_id,
        "grade_id": section.grade.public_id,
        "section_id": section.public_id,
        "student_id": active.student.public_id,
    }
    url = reverse("active-enrolment-list")
    assert [row["public_id"] for row in auth_client.get(url, params).json()["results"]] == [
        str(active.public_id)
    ]
    assert auth_client.get(url, {**params, "grade_id": uuid4()}).json()["count"] == 0


def test_candidate_can_preview_confirm_and_retry_existing_bulk_contract(auth_client):
    source_cycle = AcademicCycleFactory(year=2026, status="closed")
    section = SectionFactory(academic_cycle=source_cycle)
    source = enrol(section)
    grant(auth_client.user, institution=source_cycle.institution)
    target_cycle = AcademicCycleFactory(
        institution=source_cycle.institution,
        year=2027,
        starts_on=date(2027, 1, 1),
        ends_on=date(2027, 12, 31),
    )
    target = SectionFactory(academic_cycle=target_cycle)
    candidate = auth_client.get(
        reverse("reenrolment-candidate-list"), {"academic_cycle_id": source_cycle.public_id}
    ).json()["results"][0]
    payload = {
        "effective_on": "2027-01-15",
        "preview": True,
        "items": [
            {
                "source_enrolment_id": candidate["public_id"],
                "target_section_id": str(target.public_id),
            }
        ],
    }
    url = reverse("bulk-reenrolment-create")
    assert (
        auth_client.post(url, payload, content_type="application/json").json()["results"][0][
            "status"
        ]
        == "ready"
    )
    source.refresh_from_db()
    assert source.status == "active"
    assert not Enrolment.objects.filter(
        student=source.student, academic_cycle=target_cycle
    ).exists()
    payload["preview"] = False
    assert (
        auth_client.post(url, payload, content_type="application/json").json()["results"][0][
            "status"
        ]
        == "created"
    )
    assert (
        auth_client.post(url, payload, content_type="application/json").json()["results"][0][
            "status"
        ]
        == "existing"
    )
    assert (
        Enrolment.objects.filter(student=source.student, academic_cycle=target_cycle).count() == 1
    )
