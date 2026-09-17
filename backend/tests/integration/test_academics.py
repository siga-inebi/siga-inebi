from datetime import date

import pytest

from apps.academics.models import (
    AcademicCycle,
    CurriculumPlan,
    GradeOffering,
    Section,
    TeachingAssignment,
)
from apps.academics.queries import historical_cycle_or_404
from apps.academics.services import (
    activate_academic_cycle,
    close_academic_cycle,
    create_academic_cycle,
    create_curriculum_plan,
    create_section,
    create_teaching_assignment,
    reassign_teaching_assignment,
    reopen_academic_cycle,
)
from apps.audit.models import AuditEvent
from apps.common.models import DomainError
from apps.enrolments.models import Enrolment
from apps.evaluation.models import EvaluationUnit
from tests.factories.academic import (
    AcademicCycleFactory,
    GradeFactory,
    InstitutionFactory,
    SectionFactory,
    ShiftFactory,
    SubjectFactory,
)
from tests.factories.evaluation import EvaluationUnitFactory
from tests.factories.identity import UserFactory
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
