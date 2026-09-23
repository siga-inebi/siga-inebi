from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.academics.models import (
    AcademicCycle,
    CurriculumPlan,
    FrozenPromotionResult,
    FrozenSubjectResult,
    GradeOffering,
    LevelSubject,
    Section,
    TeachingAssignment,
)
from apps.academics.queries import historical_cycle_or_404, weekly_load_report
from apps.academics.services import (
    activate_academic_cycle,
    classroom_capacity_warning,
    clone_class_schedule,
    close_academic_cycle,
    correct_frozen_subject_result,
    create_academic_cycle,
    create_class_session,
    create_curriculum_plan,
    create_section,
    create_teaching_assignment,
    deactivate_class_session,
    reassign_teaching_assignment,
    reopen_academic_cycle,
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

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_active_cycle_closes_after_units_settle_and_then_rejects_academic_writes():
    institution = InstitutionFactory()
    actor = UserFactory()
    cycle = create_academic_cycle(
        institution=institution,
        year=2026,
        name="Ciclo 2026",
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 10, 31),
        actor=actor,
    )
    grade = GradeFactory(level__institution=institution)
    shift = ShiftFactory(campus__institution=institution)
    offering = GradeOffering.objects.create(academic_cycle=cycle, grade=grade, shift=shift)
    section = Section.objects.create(offering=offering, name="A")
    subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=grade, subject=subject)
    teacher = TeacherFactory()
    create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
        actor=actor,
    )
    activate_academic_cycle(cycle=cycle, actor=actor)
    EvaluationUnitFactory(academic_cycle=cycle, status=EvaluationUnit.UnitStatus.CLOSED)

    closed = close_academic_cycle(cycle=cycle, actor=actor)

    assert closed.status == AcademicCycle.CycleStatus.CLOSED
    assert AuditEvent.objects.filter(action="academics.cycle.closed").count() == 1
    with pytest.raises(DomainError, match="no admite cambios academicos"):
        create_teaching_assignment(
            academic_cycle=closed,
            section=section,
            subject=subject,
            teacher=TeacherFactory().person,
            actor=actor,
        )


def test_closed_cycle_reopens_for_a_grading_correction_and_can_close_again():
    """RF-CIC-005, escenario 'Correccion de un error detectado tras el
    cierre': reabrir un ciclo cerrado no descarta la estructura que ya tenia
    congelada (no existe todavia una capacidad de resultados que congelar de
    forma explicita, ver notas de RF-CIC-004); ambos cierres quedan en la
    bitacora, ninguno reemplaza al otro."""
    institution = InstitutionFactory()
    actor = UserFactory()
    cycle = create_academic_cycle(
        institution=institution,
        year=2026,
        name="Ciclo 2026",
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 10, 31),
        actor=actor,
    )
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)
    section = create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A", actor=actor)
    subject = SubjectFactory(institution=institution)
    create_curriculum_plan(academic_cycle=cycle, grade=grade, subject=subject, actor=actor)
    teacher = TeacherFactory()
    create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
        actor=actor,
    )
    cycle = activate_academic_cycle(cycle=cycle, actor=actor)
    cycle = close_academic_cycle(cycle=cycle, actor=actor)

    reopened = reopen_academic_cycle(
        cycle=cycle, reason="Se detecto una nota mal capturada", actor=actor
    )

    assert reopened.status == AcademicCycle.CycleStatus.ACTIVE
    reopen_event = AuditEvent.objects.get(action="academics.cycle.reopened")
    assert reopen_event.context["reason"] == "Se detecto una nota mal capturada"
    # La estructura congelada por el primer cierre sigue intacta: reabrir no
    # descarta nada de lo que ya existia.
    assert reopened.curriculum_plans.count() == 1
    assert reopened.teaching_assignments.filter(teacher=teacher.person).exists()
    assert Section.objects.filter(pk=section.pk, offering__academic_cycle=reopened).exists()

    reclosed = close_academic_cycle(cycle=reopened, actor=actor)

    assert reclosed.status == AcademicCycle.CycleStatus.CLOSED
    # El nuevo cierre no borra la traza del anterior: los dos quedan en la
    # bitacora (el "resultado adicional" del criterio de aceptacion depende
    # de una capacidad de resultados que todavia no existe en el codigo).
    assert AuditEvent.objects.filter(action="academics.cycle.closed").count() == 2


def test_prepared_cycle_accepts_structure_while_active_cycle_remains_current():
    institution = InstitutionFactory()
    actor = UserFactory()
    active = create_academic_cycle(
        institution=institution,
        year=2026,
        name="Ciclo 2026",
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 10, 31),
        actor=actor,
    )
    active_grade = GradeFactory(level__institution=institution)
    active_shift = ShiftFactory(campus__institution=institution)
    active_offering = GradeOffering.objects.create(
        academic_cycle=active,
        grade=active_grade,
        shift=active_shift,
    )
    active_section = Section.objects.create(offering=active_offering, name="A")
    active_subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(
        academic_cycle=active,
        grade=active_grade,
        subject=active_subject,
    )
    create_teaching_assignment(
        academic_cycle=active,
        section=active_section,
        subject=active_subject,
        teacher=TeacherFactory().person,
        actor=actor,
    )
    activate_academic_cycle(cycle=active, actor=actor)
    prepared = create_academic_cycle(
        institution=institution,
        year=2027,
        name="Ciclo 2027",
        starts_on=date(2027, 1, 1),
        ends_on=date(2027, 10, 31),
        actor=actor,
    )
    grade = GradeFactory(level__institution=institution)
    shift = ShiftFactory(campus__institution=institution)

    offering = GradeOffering.objects.create(
        academic_cycle=prepared,
        grade=grade,
        shift=shift,
    )

    assert offering.pk is not None
    assert prepared.status == AcademicCycle.CycleStatus.DRAFT
    with pytest.raises(DomainError, match="Hay que cerrar"):
        activate_academic_cycle(cycle=prepared, actor=actor)
    assert AuditEvent.objects.filter(action="academics.cycle.created").count() == 2


def test_clone_schedule_uses_target_assignments_and_records_one_summary_event():
    institution = InstitutionFactory()
    actor = UserFactory()
    cycle = AcademicCycleFactory(institution=institution)
    source_shift = ShiftFactory(campus__institution=institution)
    target_shift = ShiftFactory(campus__institution=institution)
    source_grade = GradeFactory(institution=institution)
    target_grade = GradeFactory(institution=institution)
    source = SectionFactory(academic_cycle=cycle, grade=source_grade, shift=source_shift)
    target = SectionFactory(academic_cycle=cycle, grade=target_grade, shift=target_shift)
    subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=target_grade, subject=subject)
    source_block = ClassScheduleBlockFactory(shift=source_shift, number=1)
    target_block = ClassScheduleBlockFactory(shift=target_shift, number=1)
    source_classroom = ClassroomFactory(campus=source_shift.campus)
    ClassSessionFactory(
        section=source,
        subject=subject,
        schedule_block=source_block,
        classroom=source_classroom,
    )
    target_teacher = TeacherFactory()
    TeachingAssignment.objects.create(
        academic_cycle=cycle,
        section=target,
        subject=subject,
        teacher=target_teacher.person,
        starts_on=cycle.starts_on,
    )

    cloned = clone_class_schedule(
        source_section=source,
        target_section=target,
        actor=actor,
    )

    assert len(cloned) == 1
    assert cloned[0].schedule_block == target_block
    assert cloned[0].classroom is None
    assert cloned[0].current_teacher == target_teacher.person
    event = AuditEvent.objects.get(action="academics.class_schedule.cloned")
    assert event.actor == actor
    assert event.context["source_section_id"] == source.pk
    assert event.context["target_section_id"] == target.pk
    assert event.context["session_count"] == 1


def test_active_cycle_structure_changes_do_not_alter_previous_cycle_records():
    """RF-EST-013: adding structure to the active cycle (a new teaching
    assignment) leaves a previous, already-closed cycle's own structure and
    records untouched -- each cycle's rows are independent, not a shared,
    mutable snapshot (RN-CIC-001)."""
    institution = InstitutionFactory()
    actor = UserFactory()

    previous = create_academic_cycle(
        institution=institution,
        year=2025,
        name="Ciclo 2025",
        starts_on=date(2025, 1, 1),
        ends_on=date(2025, 10, 31),
        actor=actor,
    )
    previous_grade = GradeFactory(institution=institution)
    previous_shift = ShiftFactory(campus__institution=institution)
    previous_section = create_section(
        academic_cycle=previous,
        grade=previous_grade,
        shift=previous_shift,
        name="A",
        actor=actor,
    )
    previous_subject = SubjectFactory(institution=institution)
    create_curriculum_plan(
        academic_cycle=previous, grade=previous_grade, subject=previous_subject, actor=actor
    )
    previous_teacher = TeacherFactory()
    previous_assignment = create_teaching_assignment(
        academic_cycle=previous,
        section=previous_section,
        subject=previous_subject,
        teacher=previous_teacher.person,
        actor=actor,
    )
    previous = activate_academic_cycle(cycle=previous, actor=actor)
    previous = close_academic_cycle(cycle=previous, actor=actor)

    active = create_academic_cycle(
        institution=institution,
        year=2026,
        name="Ciclo 2026",
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 10, 31),
        actor=actor,
    )
    active_grade = GradeFactory(institution=institution)
    active_shift = ShiftFactory(campus__institution=institution)
    active_section = create_section(
        academic_cycle=active,
        grade=active_grade,
        shift=active_shift,
        name="A",
        actor=actor,
    )
    active_subject = SubjectFactory(institution=institution)
    create_curriculum_plan(
        academic_cycle=active, grade=active_grade, subject=active_subject, actor=actor
    )
    active_teacher = TeacherFactory()
    create_teaching_assignment(
        academic_cycle=active,
        section=active_section,
        subject=active_subject,
        teacher=active_teacher.person,
        actor=actor,
    )
    active = activate_academic_cycle(cycle=active, actor=actor)

    previous.refresh_from_db()
    previous_section.refresh_from_db()
    previous_assignment.refresh_from_db()

    assert previous.status == AcademicCycle.CycleStatus.CLOSED
    assert previous_section.name == "A"
    assert previous_section.offering.academic_cycle_id == previous.pk
    assert previous.grade_offerings.count() == 1
    assert previous.curriculum_plans.count() == 1
    assert previous.teaching_assignments.count() == 1
    assert previous_assignment.teacher_id == previous_teacher.person.pk
    remaining_assignment = TeachingAssignment.objects.filter(academic_cycle=previous).get()
    assert remaining_assignment.pk == previous_assignment.pk


def test_created_sections_satisfy_cycle_activation_structure_check():
    institution = InstitutionFactory()
    actor = UserFactory()
    cycle = create_academic_cycle(
        institution=institution,
        year=2028,
        name="Ciclo 2028",
        starts_on=date(2028, 1, 1),
        ends_on=date(2028, 10, 31),
        actor=actor,
    )
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)

    section = create_section(
        academic_cycle=cycle, grade=grade, shift=shift, name="A", capacity=30, actor=actor
    )
    subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=grade, subject=subject)
    create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=TeacherFactory().person,
        actor=actor,
    )

    activated = activate_academic_cycle(cycle=cycle, actor=actor)

    assert activated.status == AcademicCycle.CycleStatus.ACTIVE
    assert section.offering.academic_cycle_id == cycle.pk
    assert GradeOffering.objects.filter(academic_cycle=cycle, grade=grade, shift=shift).count() == 1
    assert AuditEvent.objects.filter(action="academics.grade_offering.created").count() == 1
    assert AuditEvent.objects.filter(action="academics.section.created").count() == 1


def test_created_curriculum_plan_satisfies_activation_and_freezes_once_active():
    institution = InstitutionFactory()
    actor = UserFactory()
    cycle = create_academic_cycle(
        institution=institution,
        year=2031,
        name="Ciclo 2031",
        starts_on=date(2031, 1, 1),
        ends_on=date(2031, 10, 31),
        actor=actor,
    )
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)
    section = create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A", actor=actor)
    subject = SubjectFactory(institution=institution)
    plan = create_curriculum_plan(academic_cycle=cycle, grade=grade, subject=subject, actor=actor)
    create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=TeacherFactory().person,
        actor=actor,
    )

    activated = activate_academic_cycle(cycle=cycle, actor=actor)

    assert activated.status == AcademicCycle.CycleStatus.ACTIVE
    assert cycle.curriculum_plans.filter(pk=plan.pk).exists()
    assert AuditEvent.objects.filter(action="academics.curriculum_plan.created").count() == 1
    with pytest.raises(DomainError, match="en preparacion"):
        create_curriculum_plan(
            academic_cycle=activated,
            grade=grade,
            subject=SubjectFactory(institution=institution),
            actor=actor,
        )


def test_active_cycle_blocks_structure_but_still_allows_operational_writes():
    """
    RF-EST-011 vs RF-CIC-002: once a cycle activates, its structure (sections)
    freezes, but operational writes (a teaching assignment) stay allowed until
    the cycle actually closes.
    """
    institution = InstitutionFactory()
    actor = UserFactory()
    cycle = create_academic_cycle(
        institution=institution,
        year=2029,
        name="Ciclo 2029",
        starts_on=date(2029, 1, 1),
        ends_on=date(2029, 10, 31),
        actor=actor,
    )
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)
    section = create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A", actor=actor)
    subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=grade, subject=subject)
    teacher = TeacherFactory()
    assignment = create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
        actor=actor,
    )
    cycle = activate_academic_cycle(cycle=cycle, actor=actor)

    with pytest.raises(DomainError, match="en preparacion"):
        create_section(academic_cycle=cycle, grade=grade, shift=shift, name="B", actor=actor)

    # Structure is frozen, but an operational write on the assignment already
    # required for activation (RF-EST-010) still goes through while ACTIVE.
    successor = reassign_teaching_assignment(
        assignment=assignment,
        teacher=TeacherFactory().person,
        ends_on=cycle.starts_on,
        actor=actor,
    )
    assert successor.pk is not None
    assert successor.teacher_id != teacher.person_id


def test_historical_cycle_query_keeps_completed_enrolment_after_cycle_closes():
    cycle = AcademicCycleFactory(status=AcademicCycle.CycleStatus.CLOSED)
    section = SectionFactory(academic_cycle=cycle)
    enrolment = Enrolment.objects.create(
        student=StudentFactory(),
        academic_cycle=cycle,
        grade=section.grade,
        section=section,
        status=Enrolment.EnrolmentStatus.COMPLETED,
        ends_on=cycle.ends_on,
    )

    historical = historical_cycle_or_404(cycle.institution, cycle.public_id)

    assert historical._enrolment_total == 1
    assert historical._enrolment_completed == 1
    assert Enrolment.objects.filter(pk=enrolment.pk).exists()


def test_section_default_classroom_is_a_reference_only_not_a_requirement():
    """RF-AUL-002 (#100): el aula habitual queda registrada en la seccion y
    en la bitacora, pero es solo una referencia -- no obliga a las sesiones
    de esa seccion a llevar aula (RF-AUL-003 sigue vigente sin cambios) ni
    bloquea la activacion del ciclo (RF-CIC-003)."""
    institution = InstitutionFactory()
    actor = UserFactory()
    cycle = create_academic_cycle(
        institution=institution,
        year=2028,
        name="Ciclo 2028",
        starts_on=date(2028, 1, 1),
        ends_on=date(2028, 10, 31),
        actor=actor,
    )
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)
    classroom = ClassroomFactory(campus=shift.campus)
    section = create_section(
        academic_cycle=cycle,
        grade=grade,
        shift=shift,
        name="A",
        default_classroom=classroom,
        actor=actor,
    )
    subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=grade, subject=subject)
    create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=TeacherFactory().person,
        actor=actor,
    )
    block = ClassScheduleBlockFactory(shift=shift)
    session = create_class_session(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        schedule_block=block,
        day_of_week=1,
        actor=actor,
    )

    activated = activate_academic_cycle(cycle=cycle, actor=actor)

    assert activated.status == AcademicCycle.CycleStatus.ACTIVE
    assert section.default_classroom_id == classroom.pk
    assert session.classroom_id is None  # sigue sin exigirse (RF-AUL-003)
    creation_event = AuditEvent.objects.get(action="academics.section.created")
    assert creation_event.context["default_classroom_id"] == classroom.pk


def test_undersized_classroom_warns_but_allows_section_and_session_assignments():
    institution = InstitutionFactory()
    actor = UserFactory()
    cycle = create_academic_cycle(
        institution=institution,
        year=2028,
        name="Ciclo 2028",
        starts_on=date(2028, 1, 1),
        ends_on=date(2028, 10, 31),
        actor=actor,
    )
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)
    classroom = ClassroomFactory(campus=shift.campus, capacity=20)
    section = create_section(
        academic_cycle=cycle,
        grade=grade,
        shift=shift,
        name="A",
        capacity=30,
        default_classroom=classroom,
        actor=actor,
    )
    subject = SubjectFactory(institution=institution)
    block = ClassScheduleBlockFactory(shift=shift)

    session = create_class_session(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        schedule_block=block,
        day_of_week=1,
        classroom=classroom,
        actor=actor,
    )

    section_warning = classroom_capacity_warning(section=section, classroom=classroom)
    session_warning = classroom_capacity_warning(
        section=session.section,
        classroom=session.classroom,
    )
    assert section_warning["code"] == "classroom_capacity_below_section"
    assert session_warning == section_warning
    assert section.default_classroom == classroom
    assert session.classroom == classroom
    assert AuditEvent.objects.filter(action="academics.section.created").exists()
    assert AuditEvent.objects.filter(action="academics.class_session.created").exists()


def test_special_session_without_a_classroom_does_not_block_cycle_activation():
    """RF-AUL-003 (#101): un periodo especial (ej. Educacion Fisica) sin aula
    fija no es un hueco estructural -- no aparece entre lo que
    _academic_cycle_opening_gaps exige para activar el ciclo (RF-CIC-003)."""
    institution = InstitutionFactory()
    actor = UserFactory()
    cycle = create_academic_cycle(
        institution=institution,
        year=2028,
        name="Ciclo 2028",
        starts_on=date(2028, 1, 1),
        ends_on=date(2028, 10, 31),
        actor=actor,
    )
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)
    section = create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A", actor=actor)
    subject = SubjectFactory(institution=institution, name="Educacion Fisica")
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=grade, subject=subject)
    create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=TeacherFactory().person,
        actor=actor,
    )
    block = ClassScheduleBlockFactory(shift=shift)
    session = create_class_session(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        schedule_block=block,
        day_of_week=1,
        actor=actor,
    )
    assert session.classroom_id is None

    activated = activate_academic_cycle(cycle=cycle, actor=actor)

    assert activated.status == AcademicCycle.CycleStatus.ACTIVE


def test_weekly_load_report_reflects_the_actual_schedule_end_to_end():
    """RF-HOR-007 (#200): flujo completo -- ciclo, seccion, plan de estudios,
    carga horaria declarada a nivel de nivel educativo (RF-EST-006), y las
    sesiones realmente agendadas para esa seccion."""
    institution = InstitutionFactory()
    actor = UserFactory()
    cycle = create_academic_cycle(
        institution=institution,
        year=2026,
        name="Ciclo 2026",
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 10, 31),
        actor=actor,
    )
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)
    section = create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A", actor=actor)
    subject = SubjectFactory(institution=institution)
    create_curriculum_plan(academic_cycle=cycle, grade=grade, subject=subject, actor=actor)
    LevelSubject.objects.create(level=grade.level, subject=subject, weekly_hours=2)
    block_a = ClassScheduleBlockFactory(shift=shift, number=1)
    block_b = ClassScheduleBlockFactory(shift=shift, number=2)
    create_class_session(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        schedule_block=block_a,
        day_of_week=1,
        actor=actor,
    )

    report = weekly_load_report(section)
    row = next(r for r in report if r["subject"].pk == subject.pk)
    assert row["declared_weekly_hours"] == 2
    assert row["scheduled_periods"] == 1
    assert row["matches"] is False

    create_class_session(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        schedule_block=block_b,
        day_of_week=1,
        actor=actor,
    )

    updated_row = next(r for r in weekly_load_report(section) if r["subject"].pk == subject.pk)
    assert updated_row["scheduled_periods"] == 2
    assert updated_row["matches"] is True


def test_teacher_shared_across_two_sections_cannot_be_double_booked():
    """RF-HOR-006 (#199): a teacher assigned to two sections in the same
    cycle cannot end up scheduled in both at once -- full flow: cycle in
    preparation, two sections, a teaching assignment for each, one class
    session scheduled, then a conflicting one for the second section."""
    institution = InstitutionFactory()
    actor = UserFactory()
    cycle = create_academic_cycle(
        institution=institution,
        year=2026,
        name="Ciclo 2026",
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 10, 31),
        actor=actor,
    )
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)
    section_a = create_section(
        academic_cycle=cycle, grade=grade, shift=shift, name="A", actor=actor
    )
    section_b = create_section(
        academic_cycle=cycle, grade=grade, shift=shift, name="B", actor=actor
    )
    subject_a = SubjectFactory(institution=institution)
    subject_b = SubjectFactory(institution=institution)
    teacher = TeacherFactory()
    create_teaching_assignment(
        academic_cycle=cycle,
        section=section_a,
        subject=subject_a,
        teacher=teacher.person,
        actor=actor,
    )
    create_teaching_assignment(
        academic_cycle=cycle,
        section=section_b,
        subject=subject_b,
        teacher=teacher.person,
        actor=actor,
    )
    block = ClassScheduleBlockFactory(shift=shift)
    create_class_session(
        academic_cycle=cycle,
        section=section_a,
        subject=subject_a,
        schedule_block=block,
        day_of_week=1,
        actor=actor,
    )

    with pytest.raises(DomainError, match="El docente ya tiene otra seccion agendada"):
        create_class_session(
            academic_cycle=cycle,
            section=section_b,
            subject=subject_b,
            schedule_block=block,
            day_of_week=1,
            actor=actor,
        )

    assert section_b.class_sessions.count() == 0


def test_class_session_mid_cycle_restructuring_preserves_the_retired_slot():
    """RF-HOR-008 (#201): reestructuracion a mitad de ciclo -- se retira la
    sesion original (soft-delete, no se borra el historial) y se agenda su
    reemplazo, en otro dia, con una fecha de vigencia posterior. El slot
    original (seccion, subarea, dia, bloque) no se libera para reuso exacto
    ni siquiera desactivado -- unique_class_session_registration (RF-HOR-003)
    no distingue por is_active -- asi que la reestructuracion mueve la
    sesion a otro dia en vez de reocupar el mismo, tal como se derivaria en
    la practica de un cambio real de horario."""
    institution = InstitutionFactory()
    actor = UserFactory()
    cycle = create_academic_cycle(
        institution=institution,
        year=2026,
        name="Ciclo 2026",
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 10, 31),
        actor=actor,
    )
    grade = GradeFactory(institution=institution)
    shift = ShiftFactory(campus__institution=institution)
    section = create_section(academic_cycle=cycle, grade=grade, shift=shift, name="A", actor=actor)
    subject = SubjectFactory(institution=institution)
    block = ClassScheduleBlockFactory(shift=shift)
    original = create_class_session(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        schedule_block=block,
        day_of_week=1,
        actor=actor,
    )
    assert original.starts_on == cycle.starts_on

    deactivate_class_session(session=original, actor=actor)
    restructuring_date = date(2026, 6, 1)
    replacement = create_class_session(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        schedule_block=block,
        day_of_week=2,
        starts_on=restructuring_date,
        actor=actor,
    )

    original.refresh_from_db()
    assert original.is_active is False
    assert original.starts_on == cycle.starts_on  # el historial no cambia
    assert replacement.starts_on == restructuring_date
    assert replacement.is_active is True
    assert section.class_sessions.count() == 2


def test_closing_a_cycle_freezes_results_across_evaluation_enrolments_and_audit():
    """
    RF-RES-007: closing a cycle (academics) freezes results derived from
    live evaluation.Grade data and enrolments.determine_promotion, and a
    post-freeze correction is traceable via the audit domain -- a single
    flow crossing academics, evaluation, enrolments and audit.
    """
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
    approved_subject = SubjectFactory(institution=cycle.institution)
    failed_subject = SubjectFactory(institution=cycle.institution)
    for subject in (approved_subject, failed_subject):
        CurriculumPlan.objects.create(academic_cycle=cycle, grade=section.grade, subject=subject)
    register_unit_grade(
        enrolment=enrolment,
        subject=approved_subject,
        evaluation_unit=unit,
        teacher=PersonFactory(),
        value=90,
    )
    register_unit_grade(
        enrolment=enrolment,
        subject=failed_subject,
        evaluation_unit=unit,
        teacher=PersonFactory(),
        value=55,
    )
    close_evaluation_unit(unit)

    close_academic_cycle(cycle=cycle)

    approved_result = FrozenSubjectResult.objects.get(enrolment=enrolment, subject=approved_subject)
    failed_result = FrozenSubjectResult.objects.get(enrolment=enrolment, subject=failed_subject)
    promotion = FrozenPromotionResult.objects.get(enrolment=enrolment)
    assert approved_result.final_grade == 90
    assert approved_result.condition == "approved"
    assert failed_result.final_grade == 55
    assert failed_result.condition == "failed"
    assert promotion.promoted is False
    assert failed_subject.name in promotion.failed_subjects

    # Cambios posteriores en la estructura academica no alteran lo congelado.
    CurriculumPlan.objects.filter(subject=failed_subject).update(is_active=False)
    failed_result.refresh_from_db()
    assert failed_result.condition == "failed"

    # Correccion mediante brecha excepcional: conserva el anterior con traza.
    actor = UserFactory()
    corrected = correct_frozen_subject_result(
        frozen_result=failed_result,
        final_grade=80,
        reason="Se transcribio mal la nota de la unidad",
        actor=actor,
    )

    failed_result.refresh_from_db()
    assert failed_result.final_grade == 55
    assert corrected.final_grade == 80
    assert corrected.condition == "approved"
    event = AuditEvent.objects.get(action="academics.frozen_subject_result.corrected")
    assert event.actor_id == actor.pk
    assert event.context["reason"] == "Se transcribio mal la nota de la unidad"
    assert event.context["changes"]["final_grade"] == {"before": 55, "after": 80}
