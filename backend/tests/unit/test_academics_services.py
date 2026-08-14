from datetime import date

import pytest

from apps.academics.models import AcademicCycle, CurriculumPlan, TeachingAssignment
from apps.academics.services import (
    activate_academic_cycle,
    clone_academic_cycle,
    create_academic_cycle,
)
from apps.academics.models import AcademicCycle, CurriculumPlan
from apps.academics.services import activate_academic_cycle, create_academic_cycle
from apps.common.models import DomainError
from tests.factories.academic import (
    AcademicCycleFactory,
    GradeOfferingFactory,
    InstitutionFactory,
    SectionFactory,
    SubjectFactory,
)
from tests.factories.teachers import TeacherFactory

pytestmark = pytest.mark.django_db


def test_create_cycle_registers_requested_data_in_preparation():
    institution = InstitutionFactory()

    cycle = create_academic_cycle(
        institution=institution,
        year=2027,
        name="Ciclo 2027",
        description="Plan institucional 2027",
        starts_on=date(2027, 1, 15),
        ends_on=date(2027, 10, 31),
    )

    assert cycle.status == AcademicCycle.CycleStatus.DRAFT
    assert cycle.year == 2027
    assert cycle.description == "Plan institucional 2027"


def test_create_cycle_rejects_overlapping_dates():
    institution = InstitutionFactory()
    AcademicCycleFactory(
        institution=institution,
        year=2026,
        name="Ciclo 2026",
        starts_on=date(2026, 1, 15),
        ends_on=date(2027, 2, 28),
    )

    with pytest.raises(DomainError, match="cannot overlap"):
        create_academic_cycle(
            institution=institution,
            year=2027,
            name="Ciclo solapado",
            starts_on=date(2027, 1, 1),
            ends_on=date(2027, 6, 30),
        )


def test_activate_cycle_rejects_second_active_cycle():
    institution = InstitutionFactory()
    AcademicCycleFactory(
        institution=institution,
        year=2026,
        status=AcademicCycle.CycleStatus.ACTIVE,
    )
    prepared = AcademicCycleFactory(
        institution=institution,
        year=2027,
        starts_on=date(2027, 1, 1),
        ends_on=date(2027, 12, 31),
        status=AcademicCycle.CycleStatus.DRAFT,
    )

    with pytest.raises(DomainError, match="must be closed"):
        activate_academic_cycle(cycle=prepared)

    prepared.refresh_from_db()
    assert prepared.status == AcademicCycle.CycleStatus.DRAFT


def test_clone_cycle_copies_independent_structure_and_optional_teachers():
    source = AcademicCycleFactory(
        year=2026,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 12, 31),
        status=AcademicCycle.CycleStatus.CLOSED,
    )
    offering = GradeOfferingFactory(academic_cycle=source)
    source_section = SectionFactory(
        academic_cycle=source,
        grade=offering.grade,
        shift=offering.shift,
        name="A",
        capacity=35,
    )
    subject = SubjectFactory(institution=source.institution)
    CurriculumPlan.objects.create(
        academic_cycle=source,
        grade=offering.grade,
        subject=subject,
    )
    teacher = TeacherFactory()
    TeachingAssignment.objects.create(
        academic_cycle=source,
        section=source_section,
        subject=subject,
        teacher=teacher.person,
        starts_on=source.starts_on,
    )

    cloned = clone_academic_cycle(
        source_cycle=source,
        year=2027,
        name="Ciclo 2027",
        starts_on=date(2027, 1, 1),
        ends_on=date(2027, 12, 31),
        include_teaching_assignments=True,
    )

    cloned_section = cloned.grade_offerings.get().sections.get()
    assert cloned.status == AcademicCycle.CycleStatus.DRAFT
    assert cloned_section.pk != source_section.pk
    assert cloned_section.name == source_section.name
    assert cloned.curriculum_plans.get().subject == subject
    assert cloned.teaching_assignments.get().teacher == teacher.person
    assert cloned.teaching_assignments.get().starts_on == cloned.starts_on

    cloned_section.name = "B"
    cloned_section.save(update_fields=["name", "updated_at"])
    source_section.refresh_from_db()
    assert source_section.name == "A"


def test_clone_cycle_can_omit_teaching_assignments_and_requires_closed_source():
    source = AcademicCycleFactory(
        year=2026,
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 12, 31),
        status=AcademicCycle.CycleStatus.DRAFT,
    )

    with pytest.raises(DomainError, match="closed academic cycle"):
        clone_academic_cycle(
            source_cycle=source,
            year=2027,
            name="Ciclo 2027",
            starts_on=date(2027, 1, 1),
            ends_on=date(2027, 12, 31),
        )
def test_activate_cycle_reports_grade_without_curriculum_plan():
    prepared = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    offering = GradeOfferingFactory(academic_cycle=prepared)
    SectionFactory(academic_cycle=prepared, grade=offering.grade, shift=offering.shift)

    with pytest.raises(DomainError, match=offering.grade.name):
        activate_academic_cycle(cycle=prepared)

    prepared.refresh_from_db()
    assert prepared.status == AcademicCycle.CycleStatus.DRAFT


def test_activate_cycle_accepts_available_complete_structure():
    prepared = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    offering = GradeOfferingFactory(academic_cycle=prepared)
    SectionFactory(academic_cycle=prepared, grade=offering.grade, shift=offering.shift)
    CurriculumPlan.objects.create(
        academic_cycle=prepared,
        grade=offering.grade,
        subject=SubjectFactory(institution=prepared.institution),
    )

    activated = activate_academic_cycle(cycle=prepared)

    assert activated.status == AcademicCycle.CycleStatus.ACTIVE
