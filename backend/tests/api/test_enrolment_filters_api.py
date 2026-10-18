from datetime import date
from uuid import uuid4

import pytest
from django.urls import reverse

from apps.enrolments.models import Enrolment
from tests.factories.academic import AcademicCycleFactory, SectionFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def enrolment_in(section, **overrides):
    return Enrolment.objects.create(
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        effective_on=date(2026, 1, 15),
        **{"student": StudentFactory(), **overrides},
    )


def test_academic_filters_intersect_with_student_before_pagination(auth_client):
    cycle = AcademicCycleFactory()
    target_section = SectionFactory(academic_cycle=cycle)
    # Más de una página global: el alumno buscado no está en la primera.
    other_grade_section = SectionFactory(academic_cycle=cycle)
    for index in range(26):
        enrolment_in(
            other_grade_section,
            student=StudentFactory(student_code=f"AAA-{index:03d}"),
        )
    target = enrolment_in(target_section, student=StudentFactory(student_code="ZZZ-001"))
    same_grade_section = SectionFactory(academic_cycle=cycle, grade=target.grade)
    peer = enrolment_in(same_grade_section)
    another_cycle = AcademicCycleFactory()
    outsider = enrolment_in(SectionFactory(academic_cycle=another_cycle))
    enrolment_in(target_section, status="withdrawn")
    enrolment_in(target_section, is_active=False)
    url = reverse("active-enrolment-list")

    cycle_result = auth_client.get(url, {"academic_cycle_id": str(cycle.public_id)}).json()
    assert cycle_result["count"] == 28
    assert len(cycle_result["results"]) == 25
    grade_result = auth_client.get(url, {"grade_id": str(target.grade.public_id)}).json()
    assert grade_result["count"] == 2
    assert {row["public_id"] for row in grade_result["results"]} == {
        str(target.public_id),
        str(peer.public_id),
    }
    for filters in (
        {"section_id": str(target_section.public_id)},
        {
            "academic_cycle_id": str(cycle.public_id),
            "grade_id": str(target.grade.public_id),
            "section_id": str(target_section.public_id),
            "student_id": str(target.student.public_id),
        },
    ):
        response = auth_client.get(url, filters)
        assert response.status_code == 200
        assert response.json()["count"] == 1
        assert response.json()["results"][0]["public_id"] == str(target.public_id)
    # Filtros contradictorios no se ignoran ni amplían el resultado.
    mismatch = auth_client.get(
        url,
        {
            "academic_cycle_id": str(another_cycle.public_id),
            "section_id": str(target_section.public_id),
        },
    )
    assert mismatch.json()["count"] == 0
    assert outsider.public_id != target.public_id


@pytest.mark.parametrize("field", ["academic_cycle_id", "grade_id", "section_id"])
def test_academic_filters_reject_malformed_uuid(auth_client, field):
    response = auth_client.get(reverse("active-enrolment-list"), {field: "not-a-uuid"})
    assert response.status_code == 400


@pytest.mark.parametrize("field", ["academic_cycle_id", "grade_id", "section_id"])
def test_unknown_academic_filter_is_empty_without_falling_back(auth_client, field):
    enrolment_in(SectionFactory())
    response = auth_client.get(reverse("active-enrolment-list"), {field: str(uuid4())})
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_academic_filters_keep_session_requirement(client):
    response = client.get(reverse("active-enrolment-list"), {"academic_cycle_id": str(uuid4())})
    assert response.status_code in (401, 403)
