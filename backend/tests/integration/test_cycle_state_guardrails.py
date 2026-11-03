import re
from datetime import date
from types import SimpleNamespace

import pytest

from apps.academics.models import AcademicCycle, TeachingAssignment
from apps.academics.services import create_teaching_assignment, reassign_teaching_assignment
from apps.common.models import DomainError
from apps.enrolments.models import Enrolment
from apps.enrolments.services import change_section, create_enrolment
from tests.factories.academic import AcademicCycleFactory, SectionFactory, SubjectFactory
from tests.factories.identity import UserFactory
from tests.factories.students import StudentFactory
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def closed_cycle(db):
    """A cycle closed after it already holds an enrolment and a teaching assignment."""
    actor = UserFactory()
    cycle = AcademicCycleFactory(
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 12, 31),
    )
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory(institution=cycle.institution)
    teacher = TeacherFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=cycle,
        grade=section.grade,
        section=section,
        actor=actor,
    )
    assignment = create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
        actor=actor,
    )
    cycle.status = AcademicCycle.CycleStatus.CLOSED
    cycle.save(update_fields=["status", "updated_at"])

    return SimpleNamespace(
        actor=actor,
        cycle=cycle,
        section=section,
        subject=subject,
        enrolment=enrolment,
        assignment=assignment,
    )


def _denied_operations(scenario):
    """Every academic write that the shared cycle policy must reject, keyed by operation."""
    return {
        "enrolment.create": lambda: create_enrolment(
            student=StudentFactory(),
            academic_cycle=scenario.cycle,
            grade=scenario.section.grade,
            section=scenario.section,
            actor=scenario.actor,
        ),
        "enrolment.change_section": lambda: change_section(
            enrolment=scenario.enrolment,
            new_section=SectionFactory(academic_cycle=scenario.cycle, grade=scenario.section.grade),
            actor=scenario.actor,
        ),
        "teaching_assignment.create": lambda: create_teaching_assignment(
            academic_cycle=scenario.cycle,
            section=scenario.section,
            subject=scenario.subject,
            teacher=TeacherFactory().person,
            actor=scenario.actor,
        ),
        "teaching_assignment.reassign": lambda: reassign_teaching_assignment(
            assignment=scenario.assignment,
            teacher=TeacherFactory().person,
            ends_on=date(2026, 6, 30),
            actor=scenario.actor,
        ),
    }


@pytest.mark.parametrize(
    "operation_name",
    [
        "enrolment.create",
        "enrolment.change_section",
        "teaching_assignment.create",
        "teaching_assignment.reassign",
    ],
)
def test_closed_cycle_denies_cross_domain_write(closed_cycle, operation_name):
    operation = _denied_operations(closed_cycle)[operation_name]

    with pytest.raises(
        DomainError, match=rf"no admite cambios academicos.*{re.escape(operation_name)}"
    ):
        operation()


def test_closed_cycle_denials_preserve_history(closed_cycle):
    for operation in _denied_operations(closed_cycle).values():
        with pytest.raises(DomainError, match="ciclo escolar cerrado"):
            operation()

    closed_cycle.enrolment.refresh_from_db()
    closed_cycle.assignment.refresh_from_db()
    assert closed_cycle.enrolment.status == Enrolment.EnrolmentStatus.ACTIVE
    assert closed_cycle.assignment.ends_on is None
    assert Enrolment.objects.filter(pk=closed_cycle.enrolment.pk).exists()
    assert TeachingAssignment.objects.filter(pk=closed_cycle.assignment.pk).exists()


def test_change_section_rejects_target_section_from_another_cycle():
    """The guardrail reads the source cycle, so the target must be pinned to it too."""
    origin = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=origin.academic_cycle,
        grade=origin.grade,
        section=origin,
    )
    closed_elsewhere = AcademicCycleFactory(
        institution=origin.academic_cycle.institution,
        starts_on=date(2030, 1, 1),
        ends_on=date(2030, 12, 31),
        status="closed",
    )
    foreign_section = SectionFactory(academic_cycle=closed_elsewhere, grade=origin.grade)

    with pytest.raises(DomainError, match="seccion debe pertenecer al ciclo escolar"):
        change_section(enrolment=enrolment, new_section=foreign_section)

    enrolment.refresh_from_db()
    assert enrolment.status == Enrolment.EnrolmentStatus.ACTIVE
    assert enrolment.section_id == origin.id


def test_change_section_rejects_target_section_from_another_grade():
    origin = SectionFactory()
    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=origin.academic_cycle,
        grade=origin.grade,
        section=origin,
    )
    other_grade_section = SectionFactory(academic_cycle=origin.academic_cycle)

    with pytest.raises(DomainError, match="seccion debe pertenecer al grado"):
        change_section(enrolment=enrolment, new_section=other_grade_section)
