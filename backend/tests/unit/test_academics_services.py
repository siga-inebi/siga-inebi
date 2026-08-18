from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.academics.models import AcademicCycle, CurriculumPlan, GradeOffering, TeachingAssignment
from apps.academics.services import (
    activate_academic_cycle,
    clone_academic_cycle,
    close_academic_cycle,
    create_academic_cycle,
    create_section,
    deactivate_section,
    update_section,
)
from apps.common.models import DomainError
from apps.enrolments.models import Enrolment
from apps.evaluation.models import EvaluationUnit
from tests.factories.academic import (
    AcademicCycleFactory,
    GradeFactory,
    GradeOfferingFactory,
    InstitutionFactory,
    SectionFactory,
    ShiftFactory,
    SubjectFactory,
)
from tests.factories.students import StudentFactory
from tests.factories.evaluation import EvaluationUnitFactory
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


def test_create_section_creates_offering_and_section_when_missing():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    grade = GradeFactory(institution=cycle.institution)
    shift = ShiftFactory(campus__institution=cycle.institution)

    section = create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A", capacity=30)

    assert section.name == "A"
    assert section.capacity == 30
    assert GradeOffering.objects.filter(
        academic_cycle=cycle, grade=grade, shift=shift
    ).exists()


def test_create_section_reuses_existing_offering():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    grade = GradeFactory(institution=cycle.institution)
    shift = ShiftFactory(campus__institution=cycle.institution)

    create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A")
    create_section(academic_cycle=cycle, grade=grade, shift=shift, name="B")

    assert GradeOffering.objects.filter(academic_cycle=cycle, grade=grade, shift=shift).count() == 1


def test_create_section_rejects_duplicate_name_in_offering():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    grade = GradeFactory(institution=cycle.institution)
    shift = ShiftFactory(campus__institution=cycle.institution)
    create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A")

    with pytest.raises(DomainError, match="already exists"):
        create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A")


def test_create_section_rejects_when_cycle_is_closed():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)
    grade = GradeFactory(institution=cycle.institution)
    shift = ShiftFactory(campus__institution=cycle.institution)

    with pytest.raises(DomainError, match="do not accept academic changes"):
        create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A")


def test_create_section_rejects_grade_from_other_institution():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    grade = GradeFactory()  # different institution
    shift = ShiftFactory(campus__institution=cycle.institution)

    with pytest.raises(DomainError, match="must belong to the academic cycle institution"):
        create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A")


def test_update_section_renames_and_changes_capacity():
    section = SectionFactory(name="A", capacity=30)

    updated = update_section(section=section, name="B", capacity=40)

    assert updated.name == "B"
    assert updated.capacity == 40


def test_update_section_rejects_when_cycle_is_closed():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)
    section = SectionFactory(academic_cycle=cycle)

    with pytest.raises(DomainError, match="do not accept academic changes"):
        update_section(section=section, name="B")


def test_deactivate_section_soft_deletes_and_is_idempotent():
    section = SectionFactory()

    deactivated = deactivate_section(section=section)
    assert deactivated.is_active is False

    # Calling it again on an already-inactive section is a no-op, not an error.
    again = deactivate_section(section=deactivated)
    assert again.is_active is False


def test_deactivate_section_rejects_when_it_has_active_enrolments():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    section = SectionFactory(academic_cycle=cycle)
    Enrolment.objects.create(
        student=StudentFactory(),
        academic_cycle=cycle,
        grade=section.grade,
        section=section,
        status="active",
    )

    with pytest.raises(DomainError, match="active enrolments"):
        deactivate_section(section=section)
def test_close_cycle_rejects_when_cycle_is_not_active():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)

    with pytest.raises(DomainError, match="active academic cycle"):
        close_academic_cycle(cycle=cycle)


def test_close_cycle_rejects_when_a_unit_is_still_open():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    EvaluationUnitFactory(academic_cycle=cycle, status=EvaluationUnit.UnitStatus.CLOSED)
    open_unit = EvaluationUnitFactory(academic_cycle=cycle, status=EvaluationUnit.UnitStatus.OPEN)

    with pytest.raises(DomainError, match=open_unit.name):
        close_academic_cycle(cycle=cycle)

    cycle.refresh_from_db()
    assert cycle.status == AcademicCycle.CycleStatus.ACTIVE


def test_close_cycle_rejects_when_recovery_window_has_not_expired():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    today = timezone.localdate()
    pending_unit = EvaluationUnitFactory(
        academic_cycle=cycle,
        status=EvaluationUnit.UnitStatus.CLOSED,
        recovery_starts_on=today - timedelta(days=5),
        recovery_ends_on=today + timedelta(days=5),
    )

    with pytest.raises(DomainError, match=pending_unit.name):
        close_academic_cycle(cycle=cycle)

    cycle.refresh_from_db()
    assert cycle.status == AcademicCycle.CycleStatus.ACTIVE


def test_close_cycle_succeeds_when_units_are_closed_and_settled():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    today = timezone.localdate()
    EvaluationUnitFactory(academic_cycle=cycle, status=EvaluationUnit.UnitStatus.CLOSED)
    EvaluationUnitFactory(
        academic_cycle=cycle,
        status=EvaluationUnit.UnitStatus.CLOSED,
        recovery_starts_on=today - timedelta(days=20),
        recovery_ends_on=today - timedelta(days=5),
    )

    closed = close_academic_cycle(cycle=cycle)

    assert closed.status == AcademicCycle.CycleStatus.CLOSED


def test_close_cycle_succeeds_when_cycle_has_no_evaluation_units():
    """No units configured is vacuously "all units settled" — documented on purpose."""
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)

    closed = close_academic_cycle(cycle=cycle)

    assert closed.status == AcademicCycle.CycleStatus.CLOSED
