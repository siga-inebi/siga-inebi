from datetime import date, time, timedelta

import pytest
from django.utils import timezone

from apps.academics.models import (
    AcademicCycle,
    CurriculumPlan,
    FrozenPromotionResult,
    FrozenSubjectResult,
    GradeOffering,
    TeachingAssignment,
)
from apps.academics.services import (
    activate_academic_cycle,
    clone_academic_cycle,
    clone_class_schedule,
    close_academic_cycle,
    correct_frozen_subject_result,
    create_academic_cycle,
    create_class_schedule_block,
    create_class_session,
    create_curriculum_plan,
    create_section,
    create_teaching_assignment,
    deactivate_class_schedule_block,
    deactivate_class_session,
    deactivate_curriculum_plan,
    deactivate_section,
    freeze_cycle_results,
    publish_class_schedule,
    reopen_academic_cycle,
    unpublish_class_schedule,
    update_class_schedule_block,
    update_curriculum_plan,
    update_section,
)
from apps.audit.models import AuditEvent
from apps.common.models import DomainError
from apps.enrolments.models import Enrolment
from apps.enrolments.services import create_enrolment
from apps.evaluation.models import EvaluationUnit
from apps.evaluation.services import close_evaluation_unit, register_unit_grade
from tests.factories.academic import (
    AcademicCycleFactory,
    ClassroomFactory,
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
from tests.factories.identity import UserFactory
from tests.factories.people import PersonFactory
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


def test_clone_class_schedule_maps_blocks_and_does_not_copy_classroom():
    cycle = AcademicCycleFactory()
    source_shift = ShiftFactory(campus__institution=cycle.institution)
    target_shift = ShiftFactory(campus__institution=cycle.institution)
    source_grade = GradeFactory(institution=cycle.institution)
    target_grade = GradeFactory(institution=cycle.institution)
    source = SectionFactory(academic_cycle=cycle, grade=source_grade, shift=source_shift)
    target = SectionFactory(academic_cycle=cycle, grade=target_grade, shift=target_shift)
    subject = SubjectFactory(institution=cycle.institution)
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=target_grade, subject=subject)
    source_block = ClassScheduleBlockFactory(shift=source_shift, number=2)
    target_block = ClassScheduleBlockFactory(shift=target_shift, number=2)
    source_session = ClassSessionFactory(
        section=source,
        subject=subject,
        schedule_block=source_block,
        day_of_week=3,
        classroom=ClassroomFactory(campus=source_shift.campus),
        starts_on=cycle.starts_on + timedelta(days=14),
    )

    cloned = clone_class_schedule(source_section=source, target_section=target)

    assert len(cloned) == 1
    assert cloned[0].section == target
    assert cloned[0].subject == subject
    assert cloned[0].schedule_block == target_block
    assert cloned[0].day_of_week == source_session.day_of_week
    assert cloned[0].starts_on == source_session.starts_on
    assert cloned[0].classroom is None


def test_clone_class_schedule_rejects_nonempty_target_including_history():
    cycle = AcademicCycleFactory()
    shift = ShiftFactory(campus__institution=cycle.institution)
    source = SectionFactory(academic_cycle=cycle, shift=shift)
    target = SectionFactory(academic_cycle=cycle, shift=shift)
    subject = SubjectFactory(institution=cycle.institution)
    CurriculumPlan.objects.create(
        academic_cycle=cycle,
        grade=target.grade,
        subject=subject,
    )
    block = ClassScheduleBlockFactory(shift=shift)
    ClassSessionFactory(section=source, subject=subject, schedule_block=block)
    historical = ClassSessionFactory(
        section=target,
        subject=subject,
        schedule_block=block,
        is_active=False,
    )

    with pytest.raises(DomainError, match="historial de horario vacio"):
        clone_class_schedule(source_section=source, target_section=target)

    assert target.class_sessions.get() == historical


def test_clone_class_schedule_rolls_back_when_target_plan_is_incompatible():
    cycle = AcademicCycleFactory()
    shift = ShiftFactory(campus__institution=cycle.institution)
    source = SectionFactory(academic_cycle=cycle, shift=shift)
    target = SectionFactory(academic_cycle=cycle, shift=shift)
    block = ClassScheduleBlockFactory(shift=shift)
    included = SubjectFactory(institution=cycle.institution)
    missing = SubjectFactory(institution=cycle.institution)
    CurriculumPlan.objects.create(
        academic_cycle=cycle,
        grade=target.grade,
        subject=included,
    )
    ClassSessionFactory(section=source, subject=included, schedule_block=block, day_of_week=1)
    ClassSessionFactory(section=source, subject=missing, schedule_block=block, day_of_week=2)

    with pytest.raises(DomainError, match="no contiene todas las subareas"):
        clone_class_schedule(source_section=source, target_section=target)

    assert target.class_sessions.count() == 0


def test_clone_class_schedule_rolls_back_every_session_on_teacher_conflict():
    cycle = AcademicCycleFactory()
    shift = ShiftFactory(campus__institution=cycle.institution)
    source = SectionFactory(academic_cycle=cycle, shift=shift)
    target = SectionFactory(academic_cycle=cycle, shift=shift)
    occupied_section = SectionFactory(academic_cycle=cycle, shift=shift)
    first_subject = SubjectFactory(institution=cycle.institution)
    conflicting_subject = SubjectFactory(institution=cycle.institution)
    occupied_subject = SubjectFactory(institution=cycle.institution)
    for subject in (first_subject, conflicting_subject):
        CurriculumPlan.objects.create(
            academic_cycle=cycle,
            grade=target.grade,
            subject=subject,
        )
    first_block = ClassScheduleBlockFactory(shift=shift, number=1)
    conflicting_block = ClassScheduleBlockFactory(shift=shift, number=2)
    ClassSessionFactory(
        section=source,
        subject=first_subject,
        schedule_block=first_block,
        day_of_week=1,
    )
    ClassSessionFactory(
        section=source,
        subject=conflicting_subject,
        schedule_block=conflicting_block,
        day_of_week=2,
    )
    teacher = TeacherFactory()
    TeachingAssignment.objects.create(
        academic_cycle=cycle,
        section=target,
        subject=conflicting_subject,
        teacher=teacher.person,
        starts_on=cycle.starts_on,
    )
    TeachingAssignment.objects.create(
        academic_cycle=cycle,
        section=occupied_section,
        subject=occupied_subject,
        teacher=teacher.person,
        starts_on=cycle.starts_on,
    )
    ClassSessionFactory(
        section=occupied_section,
        subject=occupied_subject,
        schedule_block=conflicting_block,
        day_of_week=2,
    )

    with pytest.raises(DomainError, match="El docente ya tiene otra seccion agendada"):
        clone_class_schedule(source_section=source, target_section=target)

    assert target.class_sessions.count() == 0


def test_clone_class_schedule_rejects_when_target_shift_lacks_equivalent_block():
    cycle = AcademicCycleFactory()
    source_shift = ShiftFactory(campus__institution=cycle.institution)
    target_shift = ShiftFactory(campus__institution=cycle.institution)
    source = SectionFactory(academic_cycle=cycle, shift=source_shift)
    target = SectionFactory(academic_cycle=cycle, shift=target_shift)
    subject = SubjectFactory(institution=cycle.institution)
    CurriculumPlan.objects.create(
        academic_cycle=cycle,
        grade=target.grade,
        subject=subject,
    )
    source_block = ClassScheduleBlockFactory(shift=source_shift, number=3)
    ClassSessionFactory(section=source, subject=subject, schedule_block=source_block)

    with pytest.raises(DomainError, match="bloques activos equivalentes: 3"):
        clone_class_schedule(source_section=source, target_section=target)

    assert target.class_sessions.count() == 0


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


def test_reopen_cycle_rejects_when_cycle_is_not_closed():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
    with pytest.raises(DomainError, match="ciclo escolar cerrado"):
        reopen_academic_cycle(cycle=cycle, reason="Correccion de nota")
    cycle.refresh_from_db()
    assert cycle.status == AcademicCycle.CycleStatus.ACTIVE


def test_reopen_cycle_rejects_blank_reason():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)
    with pytest.raises(DomainError, match="motivo"):
        reopen_academic_cycle(cycle=cycle, reason="   ")
    cycle.refresh_from_db()
    assert cycle.status == AcademicCycle.CycleStatus.CLOSED


def test_reopen_cycle_rejects_when_another_cycle_is_already_active():
    institution = InstitutionFactory()
    AcademicCycleFactory(
        institution=institution, year=2026, status=AcademicCycle.CycleStatus.ACTIVE
    )
    closed = AcademicCycleFactory(
        institution=institution,
        year=2025,
        starts_on=date(2025, 1, 1),
        ends_on=date(2025, 10, 31),
        status=AcademicCycle.CycleStatus.CLOSED,
    )
    with pytest.raises(DomainError, match="Hay que cerrar el ciclo activo"):
        reopen_academic_cycle(cycle=closed, reason="Correccion de nota")


def test_reopen_cycle_succeeds_and_records_the_reason_in_the_audit_trail():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)
    actor = UserFactory()

    reopened = reopen_academic_cycle(
        cycle=cycle, reason="Correccion de una nota mal capturada", actor=actor
    )

    assert reopened.status == AcademicCycle.CycleStatus.ACTIVE
    event = AuditEvent.objects.get(action="academics.cycle.reopened")
    assert event.context["reason"] == "Correccion de una nota mal capturada"
    assert event.context["status"] == AcademicCycle.CycleStatus.ACTIVE


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


def test_create_section_accepts_a_default_classroom():
    """RF-AUL-002 (#100): aula habitual de referencia para la seccion."""
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory(institution=cycle.institution)
    shift = ShiftFactory(campus__institution=cycle.institution)
    classroom = ClassroomFactory(campus=shift.campus)

    section = create_section(
        academic_cycle=cycle,
        grade=grade,
        shift=shift,
        name="A",
        default_classroom=classroom,
    )

    assert section.default_classroom_id == classroom.pk


def test_create_section_rejects_default_classroom_from_another_campus():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    grade = GradeFactory(institution=cycle.institution)
    shift = ShiftFactory(campus__institution=cycle.institution)
    other_campus_classroom = ClassroomFactory()

    with pytest.raises(DomainError, match="misma sede"):
        create_section(
            academic_cycle=cycle,
            grade=grade,
            shift=shift,
            name="A",
            default_classroom=other_campus_classroom,
        )


def test_update_section_renames_and_changes_capacity():
    draft = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    section = SectionFactory(academic_cycle=draft)

    updated = update_section(section=section, name="B", capacity=40)

    assert updated.name == "B"
    assert updated.capacity == 40


def test_update_section_sets_the_default_classroom():
    """RF-AUL-002 (#100)."""
    draft = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    section = SectionFactory(academic_cycle=draft)
    classroom = ClassroomFactory(campus=section.offering.shift.campus)

    updated = update_section(section=section, default_classroom=classroom)

    assert updated.default_classroom_id == classroom.pk


def test_update_section_rejects_default_classroom_from_another_campus():
    draft = AcademicCycleFactory(status=AcademicCycle.CycleStatus.DRAFT)
    section = SectionFactory(academic_cycle=draft)
    other_campus_classroom = ClassroomFactory()

    with pytest.raises(DomainError, match="misma sede"):
        update_section(section=section, default_classroom=other_campus_classroom)


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


def test_create_class_session_does_not_require_a_classroom():
    """RF-AUL-003 (#101): periodos especiales (ej. Educacion Fisica) se
    registran sin vincular un aula fisica -- classroom ya es opcional desde
    RF-HOR-005 (#198, PR #486), sin cambios adicionales."""
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

    assert session.classroom_id is None


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


def test_create_class_session_rejects_classroom_from_a_different_campus():
    """RF-HOR-005 (#198): el aula debe pertenecer a la sede de la seccion."""
    section = SectionFactory()
    subject = SubjectFactory(institution=section.offering.institution)
    block = ClassScheduleBlockFactory(shift=section.offering.shift)
    other_campus_classroom = ClassroomFactory()

    with pytest.raises(DomainError, match="misma sede"):
        create_class_session(
            academic_cycle=section.academic_cycle,
            section=section,
            subject=subject,
            schedule_block=block,
            day_of_week=1,
            classroom=other_campus_classroom,
        )

    assert section.class_sessions.count() == 0


def test_create_class_session_rejects_classroom_double_booked_in_the_same_slot():
    """Escenario 2 (#198): cruce por aula en el mismo dia y bloque."""
    section_a = SectionFactory()
    classroom = ClassroomFactory(campus=section_a.offering.shift.campus)
    existing = ClassSessionFactory(section=section_a, classroom=classroom)
    section_b = SectionFactory(
        academic_cycle=existing.academic_cycle, shift=section_a.offering.shift
    )
    other_subject = SubjectFactory(institution=section_a.offering.institution)

    with pytest.raises(DomainError, match="El aula ya tiene otra sesion agendada"):
        create_class_session(
            academic_cycle=existing.academic_cycle,
            section=section_b,
            subject=other_subject,
            schedule_block=existing.schedule_block,
            day_of_week=existing.day_of_week,
            classroom=classroom,
        )

    assert section_b.class_sessions.count() == 0


def test_create_class_session_allows_same_classroom_in_a_different_block():
    """El aula ocupada en un dia o bloque distinto no bloquea una nueva sesion."""
    section_a = SectionFactory()
    classroom = ClassroomFactory(campus=section_a.offering.shift.campus)
    existing = ClassSessionFactory(section=section_a, classroom=classroom)
    section_b = SectionFactory(
        academic_cycle=existing.academic_cycle, shift=section_a.offering.shift
    )
    other_subject = SubjectFactory(institution=section_a.offering.institution)
    other_block = ClassScheduleBlockFactory(shift=section_b.offering.shift, number=99)

    new_session = create_class_session(
        academic_cycle=existing.academic_cycle,
        section=section_b,
        subject=other_subject,
        schedule_block=other_block,
        day_of_week=existing.day_of_week,
        classroom=classroom,
    )

    assert new_session.classroom_id == classroom.pk


def test_create_class_session_defaults_starts_on_to_the_cycle_start():
    """RF-HOR-008 (#201): sin fecha explicita, la sesion es vigente desde el
    inicio del ciclo, igual que create_teaching_assignment."""
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

    assert session.starts_on == section.academic_cycle.starts_on


def test_create_class_session_accepts_a_mid_cycle_starts_on():
    """RF-HOR-008 (#201): reestructuracion a mitad de ciclo -- se agenda con
    una fecha de vigencia posterior al inicio del ciclo."""
    section = SectionFactory()
    subject = SubjectFactory(institution=section.offering.institution)
    block = ClassScheduleBlockFactory(shift=section.offering.shift)
    mid_cycle_date = section.academic_cycle.ends_on

    session = create_class_session(
        academic_cycle=section.academic_cycle,
        section=section,
        subject=subject,
        schedule_block=block,
        day_of_week=1,
        starts_on=mid_cycle_date,
    )

    assert session.starts_on == mid_cycle_date


def test_create_class_session_rejects_starts_on_outside_the_cycle():
    section = SectionFactory()
    subject = SubjectFactory(institution=section.offering.institution)
    block = ClassScheduleBlockFactory(shift=section.offering.shift)
    before_cycle = section.academic_cycle.starts_on - timedelta(days=1)

    with pytest.raises(DomainError, match="fecha de vigencia"):
        create_class_session(
            academic_cycle=section.academic_cycle,
            section=section,
            subject=subject,
            schedule_block=block,
            day_of_week=1,
            starts_on=before_cycle,
        )

    assert section.class_sessions.count() == 0


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


def test_create_class_session_rejects_teacher_double_booked_in_the_same_slot():
    """Escenario 1 (#199): cruce por docente en el mismo dia y bloque, en
    dos secciones distintas."""
    section_a = SectionFactory()
    shift = section_a.offering.shift
    section_b = SectionFactory(academic_cycle=section_a.academic_cycle, shift=shift)
    subject_a = SubjectFactory(institution=section_a.offering.institution)
    subject_b = SubjectFactory(institution=section_a.offering.institution)
    teacher = TeacherFactory()
    create_teaching_assignment(
        academic_cycle=section_a.academic_cycle,
        section=section_a,
        subject=subject_a,
        teacher=teacher.person,
    )
    create_teaching_assignment(
        academic_cycle=section_a.academic_cycle,
        section=section_b,
        subject=subject_b,
        teacher=teacher.person,
    )
    block = ClassScheduleBlockFactory(shift=shift)
    create_class_session(
        academic_cycle=section_a.academic_cycle,
        section=section_a,
        subject=subject_a,
        schedule_block=block,
        day_of_week=1,
    )

    with pytest.raises(DomainError, match="El docente ya tiene otra seccion agendada"):
        create_class_session(
            academic_cycle=section_a.academic_cycle,
            section=section_b,
            subject=subject_b,
            schedule_block=block,
            day_of_week=1,
        )

    assert section_b.class_sessions.count() == 0


def test_create_class_session_allows_same_teacher_in_a_different_block():
    """El mismo docente en un bloque distinto no genera cruce."""
    section_a = SectionFactory()
    shift = section_a.offering.shift
    section_b = SectionFactory(academic_cycle=section_a.academic_cycle, shift=shift)
    subject_a = SubjectFactory(institution=section_a.offering.institution)
    subject_b = SubjectFactory(institution=section_a.offering.institution)
    teacher = TeacherFactory()
    create_teaching_assignment(
        academic_cycle=section_a.academic_cycle,
        section=section_a,
        subject=subject_a,
        teacher=teacher.person,
    )
    create_teaching_assignment(
        academic_cycle=section_a.academic_cycle,
        section=section_b,
        subject=subject_b,
        teacher=teacher.person,
    )
    block = ClassScheduleBlockFactory(shift=shift, number=1)
    other_block = ClassScheduleBlockFactory(shift=shift, number=2)
    create_class_session(
        academic_cycle=section_a.academic_cycle,
        section=section_a,
        subject=subject_a,
        schedule_block=block,
        day_of_week=1,
    )

    new_session = create_class_session(
        academic_cycle=section_a.academic_cycle,
        section=section_b,
        subject=subject_b,
        schedule_block=other_block,
        day_of_week=1,
    )

    assert new_session.pk is not None


def test_create_class_session_allows_double_booking_when_no_assignment_exists_yet():
    """Sin asignacion docente vigente todavia (RF-HOR-004), no hay cruce que
    detectar: el docente se resuelve como None en ambos lados."""
    section_a = SectionFactory()
    shift = section_a.offering.shift
    section_b = SectionFactory(academic_cycle=section_a.academic_cycle, shift=shift)
    subject_a = SubjectFactory(institution=section_a.offering.institution)
    subject_b = SubjectFactory(institution=section_a.offering.institution)
    block = ClassScheduleBlockFactory(shift=shift)
    create_class_session(
        academic_cycle=section_a.academic_cycle,
        section=section_a,
        subject=subject_a,
        schedule_block=block,
        day_of_week=1,
    )

    new_session = create_class_session(
        academic_cycle=section_a.academic_cycle,
        section=section_b,
        subject=subject_b,
        schedule_block=block,
        day_of_week=1,
    )

    assert new_session.pk is not None


class TestFreezeCycleResults:
    """Tests for RF-RES-007: Congelamiento al cierre del ciclo (issue #261)."""

    def _closeable_cycle_with_graded_enrolment(
        self, grades, status=Enrolment.EnrolmentStatus.ACTIVE
    ):
        cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.ACTIVE)
        today = timezone.localdate()
        unit = EvaluationUnitFactory(
            academic_cycle=cycle,
            status=EvaluationUnit.UnitStatus.OPEN,
            capture_starts_on=today - timedelta(days=30),
            capture_ends_on=today + timedelta(days=5),
            recovery_starts_on=today - timedelta(days=20),
            recovery_ends_on=today - timedelta(days=5),
        )
        section = SectionFactory(academic_cycle=cycle)
        enrolment = create_enrolment(
            student=StudentFactory(),
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )
        if status != Enrolment.EnrolmentStatus.ACTIVE:
            enrolment.status = status
            enrolment.save(update_fields=["status"])
        subjects = []
        for value in grades:
            subject = SubjectFactory(institution=cycle.institution)
            CurriculumPlan.objects.create(
                academic_cycle=cycle, grade=section.grade, subject=subject
            )
            register_unit_grade(
                enrolment=enrolment,
                subject=subject,
                evaluation_unit=unit,
                teacher=PersonFactory(),
                value=value,
            )
            subjects.append(subject)
        close_evaluation_unit(unit)
        return cycle, enrolment, subjects

    def test_closing_a_cycle_freezes_subject_results_and_promotion(self):
        cycle, enrolment, subjects = self._closeable_cycle_with_graded_enrolment([90, 55])

        close_academic_cycle(cycle=cycle)

        results = {r.subject_id: r for r in FrozenSubjectResult.objects.filter(enrolment=enrolment)}
        assert results[subjects[0].pk].final_grade == 90
        assert results[subjects[0].pk].condition == "approved"
        assert results[subjects[1].pk].final_grade == 55
        assert results[subjects[1].pk].condition == "failed"

        promotion = FrozenPromotionResult.objects.get(enrolment=enrolment)
        assert promotion.promoted is False
        assert promotion.condition == "not_promoted"
        assert subjects[1].name in promotion.failed_subjects

    def test_freeze_only_covers_enrolments_still_active_at_close(self):
        """Scope decision: a withdrawn enrolment is not frozen (RF-RES-007 only
        describes a student the cycle closed on)."""
        cycle, enrolment, _ = self._closeable_cycle_with_graded_enrolment(
            [80], status=Enrolment.EnrolmentStatus.WITHDRAWN
        )

        close_academic_cycle(cycle=cycle)

        assert not FrozenSubjectResult.objects.filter(enrolment=enrolment).exists()
        assert not FrozenPromotionResult.objects.filter(enrolment=enrolment).exists()

    def test_frozen_result_survives_a_later_configuration_change(self):
        """
        Escenario 1: Cambio de configuración posterior al cierre
        GIVEN un ciclo cerrado con resultados fijados
        WHEN se modifica la configuración de unidades de la institución
        THEN los resultados del ciclo cerrado permanecen inalterados
        """
        cycle, enrolment, subjects = self._closeable_cycle_with_graded_enrolment([70])
        close_academic_cycle(cycle=cycle)
        frozen = FrozenSubjectResult.objects.get(enrolment=enrolment, subject=subjects[0])

        # Cambia la estructura curricular del grado despues del cierre.
        CurriculumPlan.objects.filter(academic_cycle=cycle, subject=subjects[0]).update(
            is_active=False
        )
        extra_subject = SubjectFactory(institution=cycle.institution)
        CurriculumPlan.objects.create(
            academic_cycle=cycle, grade=enrolment.grade, subject=extra_subject
        )

        frozen.refresh_from_db()
        assert frozen.final_grade == 70
        assert frozen.condition == "approved"

    def test_correction_preserves_previous_frozen_value_with_trace(self):
        """
        Escenario 2: Corrección posterior al congelamiento
        GIVEN un ciclo cerrado y una nota que se determino erronea
        WHEN un usuario con permiso de autorizacion academica la corrige
             mediante brecha excepcional
        THEN el sistema registra la correccion y el nuevo resultado
        AND conserva el resultado congelado anterior con la traza del cambio
        """
        cycle, enrolment, subjects = self._closeable_cycle_with_graded_enrolment([55])
        close_academic_cycle(cycle=cycle)
        original = FrozenSubjectResult.objects.get(enrolment=enrolment, subject=subjects[0])
        actor = UserFactory()

        corrected = correct_frozen_subject_result(
            frozen_result=original,
            final_grade=75,
            reason="Error de digitacion en la nota de la tercera unidad",
            actor=actor,
        )

        assert corrected.pk != original.pk
        assert corrected.final_grade == 75
        assert corrected.condition == "approved"
        assert corrected.is_correction is True
        assert corrected.correction_reason == "Error de digitacion en la nota de la tercera unidad"

        # El resultado congelado anterior sigue existiendo y consultable.
        original.refresh_from_db()
        assert original.final_grade == 55
        assert original.condition == "failed"

        # La correccion queda en la bitacora con motivo y autor.
        event = AuditEvent.objects.get(action="academics.frozen_subject_result.corrected")
        assert event.actor_id == actor.pk
        assert event.context["reason"] == "Error de digitacion en la nota de la tercera unidad"
        assert event.context["changes"]["final_grade"] == {"before": 55, "after": 75}

    def test_correction_requires_a_reason(self):
        cycle, enrolment, subjects = self._closeable_cycle_with_graded_enrolment([55])
        close_academic_cycle(cycle=cycle)
        original = FrozenSubjectResult.objects.get(enrolment=enrolment, subject=subjects[0])

        with pytest.raises(DomainError, match="motivo de la correccion"):
            correct_frozen_subject_result(
                frozen_result=original, final_grade=75, reason="   ", actor=None
            )

    def test_correction_rejects_a_final_grade_outside_the_scale(self):
        cycle, enrolment, subjects = self._closeable_cycle_with_graded_enrolment([55])
        close_academic_cycle(cycle=cycle)
        original = FrozenSubjectResult.objects.get(enrolment=enrolment, subject=subjects[0])

        with pytest.raises(DomainError, match="entre 0 y 100"):
            correct_frozen_subject_result(
                frozen_result=original, final_grade=150, reason="Motivo", actor=None
            )

    def test_frozen_subject_result_is_immutable(self):
        cycle, enrolment, subjects = self._closeable_cycle_with_graded_enrolment([80])
        close_academic_cycle(cycle=cycle)
        frozen = FrozenSubjectResult.objects.get(enrolment=enrolment, subject=subjects[0])

        frozen.final_grade = 10
        with pytest.raises(RuntimeError, match="no pueden modificarse"):
            frozen.save()
        with pytest.raises(RuntimeError, match="no pueden modificarse"):
            FrozenSubjectResult.objects.filter(pk=frozen.pk).update(final_grade=10)
        with pytest.raises(RuntimeError, match="no pueden eliminarse"):
            frozen.delete()
        with pytest.raises(RuntimeError, match="no pueden eliminarse"):
            FrozenSubjectResult.objects.filter(pk=frozen.pk).delete()

    def test_calling_freeze_again_is_additive_not_destructive(self):
        """Extension point noted for #130 (RF-CIC-005): a future reopen-then-close
        can call freeze_cycle_results again without disturbing prior rows."""
        cycle, enrolment, subjects = self._closeable_cycle_with_graded_enrolment([80])
        close_academic_cycle(cycle=cycle)
        first = FrozenSubjectResult.objects.get(enrolment=enrolment, subject=subjects[0])

        freeze_cycle_results(cycle)

        assert (
            FrozenSubjectResult.objects.filter(enrolment=enrolment, subject=subjects[0]).count()
            == 2
        )
        first.refresh_from_db()
        assert first.final_grade == 80
