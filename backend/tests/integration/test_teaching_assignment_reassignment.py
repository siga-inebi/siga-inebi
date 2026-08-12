from datetime import date

import pytest
from django.db import IntegrityError, transaction

from apps.academics.models import TeachingAssignment
from apps.academics.services import create_teaching_assignment, reassign_teaching_assignment
from apps.audit.models import AuditEvent
from apps.common.models import DomainError
from tests.factories.academic import AcademicCycleFactory, SectionFactory, SubjectFactory
from tests.factories.teachers import TeacherFactory

pytestmark = [pytest.mark.integration, pytest.mark.postgres, pytest.mark.django_db]


def _assignment_context():
    cycle = AcademicCycleFactory(
        starts_on=date(2026, 1, 1),
        ends_on=date(2026, 12, 31),
    )
    return (
        cycle,
        SectionFactory(academic_cycle=cycle),
        SubjectFactory(institution=cycle.institution),
        TeacherFactory(),
    )


def test_reassignment_is_atomic_versioned_and_audited():
    cycle, section, subject, first_teacher = _assignment_context()
    second_teacher = TeacherFactory()
    current = create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=first_teacher.person,
    )

    successor = reassign_teaching_assignment(
        assignment=current,
        teacher=second_teacher.person,
        ends_on=date(2026, 6, 30),
    )

    current.refresh_from_db()
    assert current.ends_on == date(2026, 6, 30)
    assert successor.starts_on == date(2026, 7, 1)
    assert successor.ends_on is None
    assert TeachingAssignment.objects.filter(section=section, subject=subject).count() == 2
    event = AuditEvent.objects.latest("created_at")
    assert event.action == "academics.teaching_assignment.reassigned"
    assert event.context["previous_assignment_id"] == current.pk


def test_postgresql_exclusion_constraint_rejects_overlapping_current_assignments():
    cycle, section, subject, first_teacher = _assignment_context()
    create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=first_teacher.person,
        starts_on=date(2026, 3, 1),
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        TeachingAssignment.objects.create(
            academic_cycle=cycle,
            section=section,
            subject=subject,
            teacher=TeacherFactory().person,
            starts_on=date(2026, 4, 1),
        )


@pytest.mark.parametrize(
    ("ends_on", "message"),
    [
        (date(2025, 12, 31), "end date must be within"),
        (date(2026, 12, 31), "must leave at least one day"),
    ],
)
def test_reassignment_rejects_an_invalid_successor_period(ends_on, message):
    cycle, section, subject, first_teacher = _assignment_context()
    current = create_teaching_assignment(
        academic_cycle=cycle,
        section=section,
        subject=subject,
        teacher=first_teacher.person,
    )

    with pytest.raises(DomainError, match=message):
        reassign_teaching_assignment(
            assignment=current,
            teacher=TeacherFactory().person,
            ends_on=ends_on,
        )

    current.refresh_from_db()
    assert current.ends_on is None
