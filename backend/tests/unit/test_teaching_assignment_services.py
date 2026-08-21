from datetime import date

import pytest

from apps.academics.models import AcademicCycle
from apps.academics.services import create_teaching_assignment, reassign_teaching_assignment
from apps.common.models import DomainError
from tests.factories.academic import AcademicCycleFactory, SectionFactory, SubjectFactory
from tests.factories.people import PersonFactory
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def _assignment_context():
    cycle = AcademicCycleFactory(
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 12, 31),
    )
    section = SectionFactory(academic_cycle=cycle)
    subject = SubjectFactory(institution=cycle.institution)
    teacher = TeacherFactory()
    return cycle, section, subject, teacher


def test_create_teaching_assignment_defaults_to_cycle_start_and_requires_active_teacher():
    cycle, section, subject, teacher = _assignment_context()

    assignment = create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
    )

    assert assignment.starts_on == cycle.starts_on
    assert assignment.ends_on is None

    teacher.is_active = False
    teacher.save(update_fields=["is_active", "updated_at"])
    with pytest.raises(DomainError, match="perfil de docente activo"):
        create_teaching_assignment(
            academic_cycle=cycle,
            section=SectionFactory(academic_cycle=cycle),
            subject=subject,
            teacher=teacher.person,
        )

    with pytest.raises(DomainError, match="perfil de docente activo"):
        create_teaching_assignment(
            academic_cycle=cycle,
            section=SectionFactory(academic_cycle=cycle),
            subject=subject,
            teacher=PersonFactory(),
        )


@pytest.mark.parametrize("starts_on", [date(2025, 12, 31), date(2027, 1, 1)])
def test_create_teaching_assignment_rejects_start_outside_cycle(starts_on):
    cycle, section, subject, teacher = _assignment_context()

    with pytest.raises(DomainError, match="inicio de la asignacion debe caer dentro"):
        create_teaching_assignment(
            academic_cycle=cycle,
            section=section,
            subject=subject,
            teacher=teacher.person,
            starts_on=starts_on,
        )


def test_create_teaching_assignment_validates_section_cycle_and_subject_institution():
    cycle, _, subject, teacher = _assignment_context()
    foreign_cycle = AcademicCycleFactory(starts_on=date(2026, 1, 1), ends_on=date(2026, 12, 31))

    with pytest.raises(DomainError, match="seccion debe pertenecer"):
        create_teaching_assignment(
            academic_cycle=cycle,
            section=SectionFactory(academic_cycle=foreign_cycle),
            subject=subject,
            teacher=teacher.person,
        )

    with pytest.raises(DomainError, match="curso debe pertenecer"):
        create_teaching_assignment(
            academic_cycle=cycle,
            section=SectionFactory(academic_cycle=cycle),
            subject=SubjectFactory(),
            teacher=teacher.person,
        )


def test_closed_cycle_rejects_teaching_assignment_changes():
    cycle, section, subject, teacher = _assignment_context()
    assignment = create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=teacher.person,
    )
    cycle.status = AcademicCycle.CycleStatus.CLOSED
    cycle.save(update_fields=["status", "updated_at"])

    with pytest.raises(DomainError, match="ciclo escolar cerrado"):
        create_teaching_assignment(
            academic_cycle=cycle,
            section=section,
            subject=subject,
            teacher=TeacherFactory().person,
        )

    with pytest.raises(DomainError, match="ciclo escolar cerrado"):
        reassign_teaching_assignment(
            assignment=assignment,
            teacher=TeacherFactory().person,
            ends_on=date(2026, 6, 30),
        )
