from datetime import date

import pytest

from apps.common.models import DomainError
from apps.enrolments.models import Enrolment
from apps.enrolments.services import create_enrolment, enrolment_history, matriculate_student
from tests.factories.academic import AcademicCycleFactory, SectionFactory
from tests.factories.students import StudentFactory

pytestmark = [pytest.mark.unit, pytest.mark.django_db]


def test_create_enrolment_keeps_explicit_vigency_dates():
    section = SectionFactory()
    student = StudentFactory()

    enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        effective_on=date(2026, 2, 1),
        ends_on=date(2026, 10, 30),
    )

    assert enrolment.effective_on == date(2026, 2, 1)
    assert enrolment.ends_on == date(2026, 10, 30)
    assert enrolment.status == enrolment.EnrolmentStatus.ACTIVE


def test_enrolment_history_includes_all_statuses_and_orders_latest_first():
    student = StudentFactory()
    newest_section = SectionFactory()
    older_section = SectionFactory()
    older = Enrolment.objects.create(
        student=student,
        academic_cycle=older_section.academic_cycle,
        grade=older_section.grade,
        section=older_section,
        effective_on=date(2025, 2, 1),
        status=Enrolment.EnrolmentStatus.COMPLETED,
    )
    newest = Enrolment.objects.create(
        student=student,
        academic_cycle=newest_section.academic_cycle,
        grade=newest_section.grade,
        section=newest_section,
        effective_on=date(2026, 2, 1),
        status=Enrolment.EnrolmentStatus.ACTIVE,
    )
    newest.is_active = False
    newest.save(update_fields=["is_active", "updated_at"])

    assert list(enrolment_history(student=student)) == [newest, older]


def test_create_enrolment_rejects_grade_not_owned_by_section():
    section = SectionFactory()
    foreign_grade = SectionFactory().grade

    with pytest.raises(DomainError, match="Section must belong to the grade"):
        create_enrolment(
            student=StudentFactory(),
            academic_cycle=section.academic_cycle,
            grade=foreign_grade,
            section=section,
        )


def test_create_enrolment_rejects_closed_cycle():
    cycle = AcademicCycleFactory(status="closed")
    section = SectionFactory(academic_cycle=cycle)

    with pytest.raises(DomainError, match="Closed academic cycles"):
        create_enrolment(
            student=StudentFactory(),
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )


def test_matriculate_student_activates_pre_enrolled_student_and_links_shift():
    section = SectionFactory()
    student = StudentFactory(status="pre_enrolled")

    enrolment = matriculate_student(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        shift=section.shift,
        section=section,
        effective_on=date(2026, 2, 1),
    )

    student.refresh_from_db()
    assert enrolment.student_id == student.id
    assert enrolment.section_id == section.id
    assert section.shift.id == enrolment.section.shift.id
    assert student.status == student.StudentStatus.ACTIVE


def test_matriculate_student_rejects_student_that_is_not_pre_enrolled():
    section = SectionFactory()

    with pytest.raises(DomainError, match="Only pre-enrolled students"):
        matriculate_student(
            student=StudentFactory(),
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            shift=section.shift,
            section=section,
        )


def test_matriculate_student_rejects_shift_not_assigned_to_section():
    section = SectionFactory()
    wrong_shift = SectionFactory().shift

    with pytest.raises(DomainError, match="selected shift"):
        matriculate_student(
            student=StudentFactory(status="pre_enrolled"),
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            shift=wrong_shift,
            section=section,
        )
