from datetime import date

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


def test_closed_cycle_denies_cross_domain_writes_and_preserves_history():
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

    denied_operations = (
        (
            "enrolment.create",
            lambda: create_enrolment(
                student=StudentFactory(),
                academic_cycle=cycle,
                grade=section.grade,
                section=section,
                actor=actor,
            ),
        ),
        (
            "enrolment.change_section",
            lambda: change_section(
                enrolment=enrolment,
                new_section=SectionFactory(academic_cycle=cycle, grade=section.grade),
                actor=actor,
            ),
        ),
        (
            "teaching_assignment.create",
            lambda: create_teaching_assignment(
                academic_cycle=cycle,
                section=section,
                subject=subject,
                teacher=TeacherFactory().person,
                actor=actor,
            ),
        ),
        (
            "teaching_assignment.reassign",
            lambda: reassign_teaching_assignment(
                assignment=assignment,
                teacher=TeacherFactory().person,
                ends_on=date(2026, 6, 30),
                actor=actor,
            ),
        ),
    )

    for _, operation in denied_operations:
        with pytest.raises(DomainError, match="Closed academic cycles"):
            operation()

    enrolment.refresh_from_db()
    assignment.refresh_from_db()
    assert enrolment.status == Enrolment.EnrolmentStatus.ACTIVE
    assert assignment.ends_on is None
    assert Enrolment.objects.filter(pk=enrolment.pk).exists()
    assert TeachingAssignment.objects.filter(pk=assignment.pk).exists()
