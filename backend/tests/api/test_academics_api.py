import pytest
from django.test import Client
from django.urls import reverse

from apps.academics.models import AcademicCycle, CurriculumPlan, TeachingAssignment
from apps.audit.models import AuditEvent
from apps.enrolments.models import Enrolment
from apps.evaluation.models import EvaluationUnit
from tests.factories.academic import (
    AcademicCycleFactory,
    GradeFactory,
    GradeOfferingFactory,
    SectionFactory,
    ShiftFactory,
    SubjectFactory,
)
from tests.factories.evaluation import EvaluationUnitFactory
from tests.factories.students import StudentFactory
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.api, pytest.mark.django_db]


def test_close_cycle_api_contract(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.ACTIVE)
    EvaluationUnitFactory(academic_cycle=cycle, status=EvaluationUnit.UnitStatus.CLOSED)

    response = auth_client.post(reverse("academic-cycle-close", args=[cycle.public_id]))

    assert response.status_code == 200
    assert response.json()["status"] == "closed"


def test_close_cycle_api_rejects_open_evaluation_unit(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.ACTIVE)
    unit = EvaluationUnitFactory(academic_cycle=cycle, status=EvaluationUnit.UnitStatus.OPEN)

    response = auth_client.post(reverse("academic-cycle-close", args=[cycle.public_id]))

    assert response.status_code == 400
    assert unit.name in response.json()["error"]["detail"]


def test_close_cycle_endpoint_requires_authentication(client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.ACTIVE)
    assert client.post(reverse("academic-cycle-close", args=[cycle.public_id])).status_code == 403


def test_create_academic_cycle_contract(auth_client, institution):
    response = auth_client.post(
        reverse("academic-cycle-list-create"),
        {
            "year": 2027,
            "name": "Ciclo 2027",
            "description": "Plan institucional",
            "starts_on": "2027-01-15",
            "ends_on": "2027-10-31",
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    assert response.json()["status"] == AcademicCycle.CycleStatus.DRAFT
    assert response.json()["year"] == 2027
    assert response.json()["description"] == "Plan institucional"


def test_cycle_end_date_before_start_is_rejected(auth_client, institution):
    response = auth_client.post(
        reverse("academic-cycle-list-create"),
        {
            "year": 2027,
            "name": "Ciclo 2027",
            "starts_on": "2027-10-31",
            "ends_on": "2027-01-15",
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "cannot be before" in response.json()["error"]["detail"]


def test_activate_cycle_rejects_when_an_active_cycle_exists(auth_client, institution):
    AcademicCycleFactory(
        institution=institution,
        year=2026,
        status=AcademicCycle.CycleStatus.ACTIVE,
    )
    prepared = AcademicCycleFactory(
        institution=institution,
        year=2027,
        starts_on="2027-01-01",
        ends_on="2027-12-31",
        status=AcademicCycle.CycleStatus.DRAFT,
    )

    response = auth_client.post(reverse("academic-cycle-activate", args=[prepared.public_id]))

    assert response.status_code == 400
    assert "must be closed" in response.json()["error"]["detail"]


def test_create_section_api_creates_offering_and_section(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)

    response = auth_client.post(
        reverse("section-list-create"),
        {
            "academic_cycle_id": str(cycle.public_id),
            "grade_id": str(grade.public_id),
            "shift_id": str(shift.public_id),
            "name": "A",
            "capacity": 30,
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "A"
    assert body["capacity"] == 30
    assert body["academic_cycle_id"] == str(cycle.public_id)


def test_create_section_api_rejects_duplicate_name(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)
    payload = {
        "academic_cycle_id": str(cycle.public_id),
        "grade_id": str(grade.public_id),
        "shift_id": str(shift.public_id),
        "name": "A",
    }
    url = reverse("section-list-create")
    auth_client.post(url, payload, content_type="application/json")

    response = auth_client.post(url, payload, content_type="application/json")

    assert response.status_code == 400
    assert "already exists" in response.json()["error"]["detail"]


def test_create_section_api_rejects_when_cycle_is_active(auth_client, institution):
    """RF-EST-011: structure only changes while the cycle is still in planning."""
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.ACTIVE)
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)

    response = auth_client.post(
        reverse("section-list-create"),
        {
            "academic_cycle_id": str(cycle.public_id),
            "grade_id": str(grade.public_id),
            "shift_id": str(shift.public_id),
            "name": "A",
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "in planning" in response.json()["error"]["detail"]


def test_deactivate_section_api_contract(auth_client, institution):
    cycle = AcademicCycleFactory(institution=institution, status=AcademicCycle.CycleStatus.DRAFT)
    section = SectionFactory(academic_cycle=cycle)

    response = auth_client.delete(reverse("section-detail", args=[section.public_id]))

    assert response.status_code == 204
    section.refresh_from_db()
    assert section.is_active is False


def test_section_endpoints_require_authentication(client, institution):
    section = SectionFactory(academic_cycle=AcademicCycleFactory(institution=institution))

    assert client.get(reverse("section-list-create")).status_code == 403
    assert client.get(reverse("section-detail", args=[section.public_id])).status_code == 403


def test_cycle_endpoints_require_authentication(client, institution):
    assert client.get(reverse("academic-cycle-list-create")).status_code == 403
    response = client.post(
        reverse("academic-cycle-list-create"),
        {},
        content_type="application/json",
    )
    assert response.status_code == 403


def test_clone_cycle_api_copies_structure_and_teachers(auth_client, institution):
    source = AcademicCycleFactory(
        institution=institution,
        year=2026,
        starts_on="2026-01-01",
        ends_on="2026-12-31",
        status=AcademicCycle.CycleStatus.CLOSED,
    )
    offering = GradeOfferingFactory(academic_cycle=source)
    section = SectionFactory(
        academic_cycle=source,
        grade=offering.grade,
        shift=offering.shift,
    )
    subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(
        academic_cycle=source,
        grade=offering.grade,
        subject=subject,
    )
    teacher = TeacherFactory()
    TeachingAssignment.objects.create(
        academic_cycle=source,
        section=section,
        subject=subject,
        teacher=teacher.person,
        starts_on=source.starts_on,
    )

    response = auth_client.post(
        reverse("academic-cycle-clone", args=[source.public_id]),
        {
            "year": 2027,
            "name": "Ciclo 2027",
            "description": "Clonado de 2026",
            "starts_on": "2027-01-01",
            "ends_on": "2027-12-31",
            "include_teaching_assignments": True,
        },
        content_type="application/json",
    )

    assert response.status_code == 201
    cloned = AcademicCycle.objects.get(public_id=response.json()["public_id"])
    assert cloned.status == AcademicCycle.CycleStatus.DRAFT
    assert cloned.grade_offerings.count() == 1
    assert cloned.grade_offerings.get().sections.count() == 1
    assert cloned.curriculum_plans.count() == 1
    assert cloned.teaching_assignments.count() == 1
    event = AuditEvent.objects.get(action="academics.cycle.cloned")
    assert event.context["source_cycle_id"] == source.pk
    assert event.context["teaching_assignment_count"] == 1


def test_closed_cycle_historical_detail_preserves_structure_and_aggregates_enrolments(
    auth_client, institution
):
    cycle = AcademicCycleFactory(
        institution=institution,
        status=AcademicCycle.CycleStatus.CLOSED,
    )
    offering = GradeOfferingFactory(academic_cycle=cycle)
    section = SectionFactory(
        academic_cycle=cycle,
        grade=offering.grade,
        shift=offering.shift,
        is_active=False,
    )
    subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(
        academic_cycle=cycle,
        grade=offering.grade,
        subject=subject,
        is_active=False,
    )
    teacher = TeacherFactory()
    TeachingAssignment.objects.create(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
        starts_on=cycle.starts_on,
        ends_on=cycle.ends_on,
        is_active=False,
    )
    for status in Enrolment.EnrolmentStatus.values:
        Enrolment.objects.create(
            student=StudentFactory(),
            academic_cycle=cycle,
            grade=offering.grade,
            section=section,
            status=status,
        )

    response = auth_client.get(reverse("academic-cycle-historical-detail", args=[cycle.public_id]))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == AcademicCycle.CycleStatus.CLOSED
    assert payload["grade_offerings"][0]["sections"][0]["is_active"] is False
    assert payload["curriculum_plans"][0]["is_active"] is False
    assert payload["teaching_assignments"][0]["ends_on"] == str(cycle.ends_on)
    assert payload["enrolments"] == {
        "total": 4,
        "active": 1,
        "withdrawn": 1,
        "completed": 1,
        "cancelled": 1,
    }


def test_historical_cycle_detail_is_institution_bound_and_requires_authentication(
    auth_client, institution
):
    foreign_cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)
    anonymous_client = Client()

    assert (
        anonymous_client.get(
            reverse("academic-cycle-historical-detail", args=[foreign_cycle.public_id])
        ).status_code
        == 403
    )
    assert (
        auth_client.get(
            reverse("academic-cycle-historical-detail", args=[foreign_cycle.public_id])
        ).status_code
        == 404
    )
