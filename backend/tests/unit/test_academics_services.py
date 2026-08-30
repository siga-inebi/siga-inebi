from datetime import date, time, timedelta

import pytest
from django.utils import timezone

from apps.academics.models import AcademicCycle, CurriculumPlan, GradeOffering, TeachingAssignment
from apps.academics.services import (
    activate_academic_cycle,
    clone_academic_cycle,
    close_academic_cycle,
    create_academic_cycle,
    create_class_schedule_block,
    create_class_session,
    create_curriculum_plan,
    create_section,
    deactivate_class_schedule_block,
    deactivate_class_session,
    deactivate_curriculum_plan,
    deactivate_section,
    publish_class_schedule,
    unpublish_class_schedule,
    update_class_schedule_block,
    update_curriculum_plan,
    update_section,
)
from apps.common.models import DomainError
from apps.enrolments.models import Enrolment
from apps.evaluation.models import EvaluationUnit
from tests.factories.academic import (
    AcademicCycleFactory,
    ClassScheduleBlockFactory,
    ClassSessionFactory,
    GradeFactory,
    GradeOfferingFactory,
    InstitutionFactory,
    SectionFactory,
    ShiftFactory,
    SubjectFactory,
)
from tests.factories.evaluation import EvaluationUnitFactory
from tests.factories.students import StudentFactory
from tests.factories.teachers import TeacherFactory

pytestmark = pytest.mark.django_db


def test_close_cycle_rejects_when_cycle_is_not_active():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    with pytest.raises(DomainError, match="ciclo escolar activo"):
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
    assert close_academic_cycle(cycle=cycle).status == AcademicCycle.CycleStatus.CLOSED


def test_close_cycle_succeeds_when_cycle_has_no_evaluation_units():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    assert close_academic_cycle(cycle=cycle).status == AcademicCycle.CycleStatus.CLOSED


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

    with pytest.raises(DomainError, match="Hay que cerrar"):
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

    with pytest.raises(DomainError, match="ciclo escolar cerrado"):
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
    section = SectionFactory(academic_cycle=prepared, grade=offering.grade, shift=offering.shift)
    subject = SubjectFactory(institution=prepared.institution)
    CurriculumPlan.objects.create(
        academic_cycle=prepared,
        grade=offering.grade,
        subject=subject,
    )
    TeachingAssignment.objects.create(
        academic_cycle=prepared,
        section=section,
        subject=subject,
        teacher=TeacherFactory().person,
        starts_on=prepared.starts_on,
    )

    activated = activate_academic_cycle(cycle=prepared)

    assert activated.status == AcademicCycle.CycleStatus.ACTIVE


def test_activate_cycle_reports_section_subject_without_teacher():
    """RF-EST-010: every subarea of every configured section needs a current teacher."""
    prepared = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    offering = GradeOfferingFactory(academic_cycle=prepared)
    section = SectionFactory(academic_cycle=prepared, grade=offering.grade, shift=offering.shift)
    subject = SubjectFactory(institution=prepared.institution)
    CurriculumPlan.objects.create(
        academic_cycle=prepared,
        grade=offering.grade,
        subject=subject,
    )

    with pytest.raises(DomainError, match=f"{subject.name}.*{section.name}"):
        activate_academic_cycle(cycle=prepared)

    prepared.refresh_from_db()
    assert prepared.status == AcademicCycle.CycleStatus.DRAFT


def test_activate_cycle_reports_subject_whose_only_teacher_assignment_has_ended():
    """A closed (reassigned) teaching assignment does not count as current coverage."""
    prepared = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    offering = GradeOfferingFactory(academic_cycle=prepared)
    section = SectionFactory(academic_cycle=prepared, grade=offering.grade, shift=offering.shift)
    subject = SubjectFactory(institution=prepared.institution)
    CurriculumPlan.objects.create(
        academic_cycle=prepared,
        grade=offering.grade,
        subject=subject,
    )
    TeachingAssignment.objects.create(
        academic_cycle=prepared,
        section=section,
        subject=subject,
        teacher=TeacherFactory().person,
        starts_on=prepared.starts_on,
        ends_on=prepared.starts_on + timedelta(days=30),
    )

    with pytest.raises(DomainError, match=f"{subject.name}.*{section.name}"):
        activate_academic_cycle(cycle=prepared)


def test_create_section_creates_offering_and_section_when_missing():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory(institution=cycle.institution)
    shift = ShiftFactory(campus__institution=cycle.institution)

    section = create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A", capacity=30)

    assert section.name == "A"
    assert section.capacity == 30
    assert GradeOffering.objects.filter(academic_cycle=cycle, grade=grade, shift=shift).exists()


def test_create_section_reuses_existing_offering():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory(institution=cycle.institution)
    shift = ShiftFactory(campus__institution=cycle.institution)

    create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A")
    create_section(academic_cycle=cycle, grade=grade, shift=shift, name="B")

    assert GradeOffering.objects.filter(academic_cycle=cycle, grade=grade, shift=shift).count() == 1


def test_create_section_rejects_duplicate_name_in_offering():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory(institution=cycle.institution)
    shift = ShiftFactory(campus__institution=cycle.institution)
    create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A")

    with pytest.raises(DomainError, match="already exists"):
        create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A")


def test_create_section_rejects_when_cycle_is_closed():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)
    grade = GradeFactory(institution=cycle.institution)
    shift = ShiftFactory(campus__institution=cycle.institution)

    with pytest.raises(DomainError, match="no admite cambios academicos"):
        create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A")


def test_create_section_rejects_when_cycle_is_active():
    """RF-EST-011: structure only changes while the cycle is still in planning."""
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    grade = GradeFactory(institution=cycle.institution)
    shift = ShiftFactory(campus__institution=cycle.institution)

    with pytest.raises(DomainError, match="en preparacion"):
        create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A")


def test_create_section_rejects_grade_from_other_institution():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory()  # different institution
    shift = ShiftFactory(campus__institution=cycle.institution)

    with pytest.raises(DomainError, match="institucion del ciclo escolar"):
        create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A")


def test_update_section_renames_and_changes_capacity():
    draft = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    section = SectionFactory(academic_cycle=draft)

    updated = update_section(section=section, name="B", capacity=40)

    assert updated.name == "B"
    assert updated.capacity == 40


def test_update_section_rejects_when_cycle_is_closed():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)
    section = SectionFactory(academic_cycle=cycle)

    with pytest.raises(DomainError, match="no admite cambios academicos"):
        update_section(section=section, name="B")


def test_update_section_rejects_when_cycle_is_active():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    section = SectionFactory(academic_cycle=cycle)

    with pytest.raises(DomainError, match="en preparacion"):
        update_section(section=section, name="B")


def test_deactivate_section_soft_deletes_and_is_idempotent():
    draft = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    section = SectionFactory(academic_cycle=draft)

    deactivated = deactivate_section(section=section)
    assert deactivated.is_active is False

    # Calling it again on an already-inactive section is a no-op, not an error.
    again = deactivate_section(section=deactivated)
    assert again.is_active is False


def test_deactivate_section_rejects_when_cycle_is_active():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    section = SectionFactory(academic_cycle=cycle)

    with pytest.raises(DomainError, match="en preparacion"):
        deactivate_section(section=section)


def test_deactivate_section_rejects_when_it_has_active_enrolments():
    # Draft on purpose: isolates the enrolment check from the RF-EST-011 planning guard.
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    section = SectionFactory(academic_cycle=cycle)
    Enrolment.objects.create(
        student=StudentFactory(),
        academic_cycle=cycle,
        grade=section.grade,
        section=section,
        status="active",
    )

    with pytest.raises(DomainError, match="matriculas activas"):
        deactivate_section(section=section)


def test_create_curriculum_plan_assigns_subject_to_grade():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory(institution=cycle.institution)
    subject = SubjectFactory(institution=cycle.institution)

    plan = create_curriculum_plan(academic_cycle=cycle, grade=grade, subject=subject)

    assert plan.academic_cycle_id == cycle.pk
    assert plan.grade_id == grade.pk
    assert plan.subject_id == subject.pk
    assert plan.is_required is True


def test_create_curriculum_plan_rejects_duplicate_subject_for_grade_and_cycle():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory(institution=cycle.institution)
    subject = SubjectFactory(institution=cycle.institution)
    create_curriculum_plan(academic_cycle=cycle, grade=grade, subject=subject)

    with pytest.raises(DomainError, match="already part of the curriculum plan"):
        create_curriculum_plan(academic_cycle=cycle, grade=grade, subject=subject)


def test_create_curriculum_plan_rejects_when_cycle_is_closed():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)
    grade = GradeFactory(institution=cycle.institution)
    subject = SubjectFactory(institution=cycle.institution)

    with pytest.raises(DomainError, match="no admite cambios academicos"):
        create_curriculum_plan(academic_cycle=cycle, grade=grade, subject=subject)


def test_create_curriculum_plan_rejects_when_cycle_is_active():
    """RF-EST-011: the study plan is structure, only changes while the cycle is in planning."""
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    grade = GradeFactory(institution=cycle.institution)
    subject = SubjectFactory(institution=cycle.institution)

    with pytest.raises(DomainError, match="en preparacion"):
        create_curriculum_plan(academic_cycle=cycle, grade=grade, subject=subject)


def test_create_curriculum_plan_rejects_grade_from_other_institution():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory()  # different institution
    subject = SubjectFactory(institution=cycle.institution)

    with pytest.raises(DomainError, match="institucion del ciclo escolar"):
        create_curriculum_plan(academic_cycle=cycle, grade=grade, subject=subject)


def test_update_curriculum_plan_changes_is_required():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    plan = create_curriculum_plan(
        academic_cycle=cycle,
        grade=GradeFactory(institution=cycle.institution),
        subject=SubjectFactory(institution=cycle.institution),
    )

    updated = update_curriculum_plan(plan=plan, is_required=False)

    assert updated.is_required is False


def test_update_curriculum_plan_rejects_when_cycle_is_active():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    plan = create_curriculum_plan(
        academic_cycle=cycle,
        grade=GradeFactory(institution=cycle.institution),
        subject=SubjectFactory(institution=cycle.institution),
    )
    cycle.status = AcademicCycle.CycleStatus.ACTIVE
    cycle.save(update_fields=["status", "updated_at"])

    with pytest.raises(DomainError, match="en preparacion"):
        update_curriculum_plan(plan=plan, is_required=False)


def test_deactivate_curriculum_plan_soft_deletes_and_is_idempotent():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    plan = create_curriculum_plan(
        academic_cycle=cycle,
        grade=GradeFactory(institution=cycle.institution),
        subject=SubjectFactory(institution=cycle.institution),
    )

    deactivated = deactivate_curriculum_plan(plan=plan)
    assert deactivated.is_active is False

    again = deactivate_curriculum_plan(plan=deactivated)
    assert again.is_active is False


def test_deactivate_curriculum_plan_rejects_when_cycle_is_active():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    plan = create_curriculum_plan(
        academic_cycle=cycle,
        grade=GradeFactory(institution=cycle.institution),
        subject=SubjectFactory(institution=cycle.institution),
    )
    cycle.status = AcademicCycle.CycleStatus.ACTIVE
    cycle.save(update_fields=["status", "updated_at"])

    with pytest.raises(DomainError, match="en preparacion"):
        deactivate_curriculum_plan(plan=plan)


# --------------------------------------------------------------------------- #
# class schedule blocks (RF-HOR-001)
# --------------------------------------------------------------------------- #


def test_create_class_schedule_block_registers_requested_block():
    """Escenario 1 (#194): registro de un bloque valido dentro de la jornada."""
    shift = ShiftFactory()

    block = create_class_schedule_block(
        shift=shift, number=1, name="Bloque 1", starts_on=time(7, 0), ends_on=time(7, 45)
    )

    assert block.shift_id == shift.pk
    assert block.number == 1
    assert block.starts_on == time(7, 0)
    assert block.ends_on == time(7, 45)


def test_create_class_schedule_block_rejects_overlapping_block():
    """Escenario 2 (#194): rechazo por bloques solapados en la misma jornada."""
    shift = ShiftFactory()
    existing = ClassScheduleBlockFactory(
        shift=shift, number=1, starts_on=time(7, 0), ends_on=time(7, 45)
    )

    with pytest.raises(DomainError, match="se solapa"):
        create_class_schedule_block(
            shift=shift, number=2, name="Bloque 2", starts_on=time(7, 30), ends_on=time(8, 15)
        )

    assert shift.schedule_blocks.count() == 1
    existing.refresh_from_db()
    assert existing.starts_on == time(7, 0)


def test_create_class_schedule_block_allows_adjacent_block():
    """A block that starts exactly when the previous one ends does not overlap."""
    shift = ShiftFactory()
    ClassScheduleBlockFactory(shift=shift, number=1, starts_on=time(7, 0), ends_on=time(7, 45))

    block = create_class_schedule_block(
        shift=shift, number=2, name="Bloque 2", starts_on=time(7, 45), ends_on=time(8, 30)
    )

    assert block.starts_on == time(7, 45)


def test_create_class_schedule_block_rejects_invalid_times():
    shift = ShiftFactory()

    with pytest.raises(DomainError, match="anterior a la hora de fin"):
        create_class_schedule_block(
            shift=shift, number=1, name="Bloque 1", starts_on=time(8, 0), ends_on=time(7, 0)
        )


def test_create_class_schedule_block_rejects_duplicate_number():
    shift = ShiftFactory()
    ClassScheduleBlockFactory(shift=shift, number=1, starts_on=time(7, 0), ends_on=time(7, 45))

    with pytest.raises(DomainError, match="Schedule block number 1"):
        create_class_schedule_block(
            shift=shift, number=1, name="Otro bloque", starts_on=time(9, 0), ends_on=time(9, 45)
        )


def test_create_class_schedule_block_rejects_when_shift_inactive():
    shift = ShiftFactory(is_active=False)

    with pytest.raises(DomainError, match="la jornada"):
        create_class_schedule_block(
            shift=shift, number=1, name="Bloque 1", starts_on=time(7, 0), ends_on=time(7, 45)
        )


def test_update_class_schedule_block_rejects_overlap_with_other_block():
    shift = ShiftFactory()
    ClassScheduleBlockFactory(shift=shift, number=1, starts_on=time(7, 0), ends_on=time(7, 45))
    second = ClassScheduleBlockFactory(
        shift=shift, number=2, starts_on=time(8, 0), ends_on=time(8, 45)
    )

    with pytest.raises(DomainError, match="se solapa"):
        update_class_schedule_block(block=second, starts_on=time(7, 30))

    second.refresh_from_db()
    assert second.starts_on == time(8, 0)


def test_update_class_schedule_block_allows_retiming_without_collision():
    shift = ShiftFactory()
    block = ClassScheduleBlockFactory(
        shift=shift, number=1, starts_on=time(7, 0), ends_on=time(7, 45)
    )

    updated = update_class_schedule_block(block=block, name="Bloque renombrado", ends_on=time(8, 0))

    assert updated.name == "Bloque renombrado"
    assert updated.ends_on == time(8, 0)


def test_deactivate_class_schedule_block_is_idempotent():
    block = ClassScheduleBlockFactory()

    deactivated = deactivate_class_schedule_block(block=block)
    assert deactivated.is_active is False

    again = deactivate_class_schedule_block(block=deactivated)
    assert again.is_active is False


# --------------------------------------------------------------------------- #
# class sessions (RF-HOR-003)
# --------------------------------------------------------------------------- #


def test_create_class_session_registers_requested_session():
    """Escenario 1 (#196): agendar una sesion valida."""
    section = SectionFactory()
    subject = SubjectFactory(institution=section.offering.institution)
    block = ClassScheduleBlockFactory(shift=section.offering.shift)

    session = create_class_session(
        academic_cycle=section.academic_cycle,
        section=section,
        subject=subject,
        schedule_block=block,
        day_of_week=1,
    )

    assert session.section_id == section.pk
    assert session.subject_id == subject.pk
    assert session.schedule_block_id == block.pk
    assert session.day_of_week == 1


def test_create_class_session_rejects_block_from_a_different_shift():
    """Escenario 2 (#196): el bloque debe pertenecer a la jornada de la seccion."""
    section = SectionFactory()
    subject = SubjectFactory(institution=section.offering.institution)
    other_shift_block = ClassScheduleBlockFactory()

    with pytest.raises(DomainError, match="misma jornada"):
        create_class_session(
            academic_cycle=section.academic_cycle,
            section=section,
            subject=subject,
            schedule_block=other_shift_block,
            day_of_week=1,
        )

    assert section.class_sessions.count() == 0


def test_create_class_session_rejects_section_from_a_different_cycle():
    section = SectionFactory()
    subject = SubjectFactory(institution=section.offering.institution)
    block = ClassScheduleBlockFactory(shift=section.offering.shift)
    other_cycle = AcademicCycleFactory(
        institution=section.offering.institution,
        starts_on=date(section.academic_cycle.starts_on.year + 1, 1, 1),
        status=AcademicCycle.CycleStatus.DRAFT,
    )

    with pytest.raises(DomainError, match="ciclo escolar"):
        create_class_session(
            academic_cycle=other_cycle,
            section=section,
            subject=subject,
            schedule_block=block,
            day_of_week=1,
        )


def test_create_class_session_rejects_exact_duplicate_registration():
    session = ClassSessionFactory()

    with pytest.raises(DomainError, match="ya esta registrada"):
        create_class_session(
            academic_cycle=session.academic_cycle,
            section=session.section,
            subject=session.subject,
            schedule_block=session.schedule_block,
            day_of_week=session.day_of_week,
        )


def test_create_class_session_rejects_section_double_booked_in_the_same_slot():
    """Escenario 1 (#198): cruce por seccion en el mismo dia y bloque."""
    session = ClassSessionFactory()
    other_subject = SubjectFactory(institution=session.section.offering.institution)

    with pytest.raises(DomainError, match="cruce de horario"):
        create_class_session(
            academic_cycle=session.academic_cycle,
            section=session.section,
            subject=other_subject,
            schedule_block=session.schedule_block,
            day_of_week=session.day_of_week,
        )

    assert session.section.class_sessions.count() == 1


def test_create_class_session_allows_same_section_in_a_different_block():
    session = ClassSessionFactory()
    other_subject = SubjectFactory(institution=session.section.offering.institution)
    other_block = ClassScheduleBlockFactory(shift=session.section.offering.shift, number=99)

    new_session = create_class_session(
        academic_cycle=session.academic_cycle,
        section=session.section,
        subject=other_subject,
        schedule_block=other_block,
        day_of_week=session.day_of_week,
    )

    assert new_session.section.class_sessions.count() == 2


def test_create_class_session_ignores_a_deactivated_session_in_the_same_slot():
    """A soft-deleted session no longer occupies its slot."""
    session = ClassSessionFactory()
    other_subject = SubjectFactory(institution=session.section.offering.institution)
    deactivate_class_session(session=session)

    new_session = create_class_session(
        academic_cycle=session.academic_cycle,
        section=session.section,
        subject=other_subject,
        schedule_block=session.schedule_block,
        day_of_week=session.day_of_week,
    )

    assert new_session.pk != session.pk


def test_deactivate_class_session_is_idempotent():
    session = ClassSessionFactory()

    deactivated = deactivate_class_session(session=session)
    assert deactivated.is_active is False

    again = deactivate_class_session(session=deactivated)
    assert again.is_active is False


# --------------------------------------------------------------------------- #
# derived teacher on class sessions (RF-HOR-004)
# --------------------------------------------------------------------------- #


def test_class_session_current_teacher_matches_the_current_assignment():
    """Escenario 1 (#197): el docente se deriva de la asignacion vigente."""
    session = ClassSessionFactory()
    teacher = TeacherFactory()
    TeachingAssignment.objects.create(
        academic_cycle=session.academic_cycle,
        section=session.section,
        subject=session.subject,
        teacher=teacher.person,
        starts_on=session.academic_cycle.starts_on,
    )

    assert session.current_teacher == teacher.person


def test_class_session_current_teacher_is_none_without_a_current_assignment():
    """Escenario 2 (#197): sin asignacion vigente, el docente derivado es nulo."""
    session = ClassSessionFactory()

    assert session.current_teacher is None


def test_class_session_current_teacher_ignores_a_closed_assignment():
    """A reassigned (closed) assignment does not count as current coverage."""
    session = ClassSessionFactory()
    former_teacher = TeacherFactory()
    TeachingAssignment.objects.create(
        academic_cycle=session.academic_cycle,
        section=session.section,
        subject=session.subject,
        teacher=former_teacher.person,
        starts_on=session.academic_cycle.starts_on,
        ends_on=session.academic_cycle.starts_on + timedelta(days=30),
    )

    assert session.current_teacher is None


# --------------------------------------------------------------------------- #
# class schedule publication (RF-HOR-009)
# --------------------------------------------------------------------------- #


def test_publish_class_schedule_marks_it_published():
    """Escenario 1 (#202): publicar el horario del ciclo."""
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)

    publication = publish_class_schedule(academic_cycle=cycle)

    assert publication.is_published is True
    assert publication.published_at is not None


def test_publish_class_schedule_rejects_closed_cycle():
    """Escenario 2 (#202): rechazo por ciclo cerrado."""
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)

    with pytest.raises(DomainError, match="no admite cambios academicos"):
        publish_class_schedule(academic_cycle=cycle)


def test_publish_class_schedule_is_idempotent():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    first = publish_class_schedule(academic_cycle=cycle)

    second = publish_class_schedule(academic_cycle=cycle)

    assert second.pk == first.pk
    assert second.is_published is True


def test_unpublish_class_schedule_reverts_to_draft():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    publish_class_schedule(academic_cycle=cycle)

    publication = unpublish_class_schedule(academic_cycle=cycle)

    assert publication.is_published is False
    assert publication.published_at is None


def test_unpublish_class_schedule_is_a_no_op_when_never_published():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)

    publication = unpublish_class_schedule(academic_cycle=cycle)

    assert publication.is_published is False


def test_unpublish_class_schedule_rejects_closed_cycle():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)

    with pytest.raises(DomainError, match="no admite cambios academicos"):
        unpublish_class_schedule(academic_cycle=cycle)
