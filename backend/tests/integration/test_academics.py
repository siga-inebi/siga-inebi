from datetime import date

import pytest

from apps.academics.api.queries import historical_cycle_or_404
from apps.academics.models import AcademicCycle, CurriculumPlan, GradeOffering, Section
from apps.academics.services import (
    activate_academic_cycle,
    create_academic_cycle,
    create_section,
from apps.academics.services import activate_academic_cycle, create_academic_cycle, create_section
from apps.academics.services import (
    activate_academic_cycle,
    close_academic_cycle,
    create_academic_cycle,
    create_teaching_assignment,
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
    Section.objects.create(offering=active_offering, name="A")
    CurriculumPlan.objects.create(
        academic_cycle=active,
        grade=active_grade,
        subject=SubjectFactory(institution=institution),
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
    with pytest.raises(DomainError, match="must be closed"):
        activate_academic_cycle(cycle=prepared, actor=actor)
    assert AuditEvent.objects.filter(action="academics.cycle.created").count() == 2


def test_created_sections_satisfy_cycle_activation_structure_check():
def test_active_cycle_closes_after_units_settle_and_then_rejects_academic_writes():
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
    CurriculumPlan.objects.create(
        academic_cycle=cycle, grade=grade, subject=SubjectFactory(institution=institution)
    )

    activated = activate_academic_cycle(cycle=cycle, actor=actor)

    assert activated.status == AcademicCycle.CycleStatus.ACTIVE
    assert section.offering.academic_cycle_id == cycle.pk
    assert GradeOffering.objects.filter(academic_cycle=cycle, grade=grade, shift=shift).count() == 1
    assert AuditEvent.objects.filter(action="academics.grade_offering.created").count() == 1
    assert AuditEvent.objects.filter(action="academics.section.created").count() == 1


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
    section = create_section(
        academic_cycle=cycle, grade=grade, shift=shift, name="A", actor=actor
    )
    subject = SubjectFactory(institution=institution)
    CurriculumPlan.objects.create(academic_cycle=cycle, grade=grade, subject=subject)
    cycle = activate_academic_cycle(cycle=cycle, actor=actor)

    with pytest.raises(DomainError, match="in planning"):
        create_section(academic_cycle=cycle, grade=grade, shift=shift, name="B", actor=actor)

    teacher = TeacherFactory()
    assignment = create_teaching_assignment(
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
    activate_academic_cycle(cycle=cycle, actor=actor)
    EvaluationUnitFactory(academic_cycle=cycle, status=EvaluationUnit.UnitStatus.CLOSED)
    teacher = TeacherFactory()
    create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
        actor=actor,
    )
    assert assignment.pk is not None

    closed = close_academic_cycle(cycle=cycle, actor=actor)

    assert closed.status == AcademicCycle.CycleStatus.CLOSED
    assert AuditEvent.objects.filter(action="academics.cycle.closed").count() == 1
    with pytest.raises(DomainError, match="do not accept academic changes"):
        create_teaching_assignment(
            academic_cycle=closed,
            section=section,
            subject=subject,
            teacher=TeacherFactory().person,
            actor=actor,
        )


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
