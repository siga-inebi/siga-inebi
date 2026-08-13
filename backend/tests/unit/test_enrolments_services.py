from datetime import date

import pytest

from apps.common.models import DomainError
from apps.enrolments.models import Enrolment
from apps.enrolments.services import (
    change_section,
    create_enrolment,
    matriculate_student,
    reenrol_student,
)
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


def test_create_enrolment_rejects_full_section():
    section = SectionFactory(capacity=1)
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    with pytest.raises(DomainError, match="Section capacity has been reached"):
        create_enrolment(
            student=StudentFactory(),
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            section=section,
        )


def test_create_enrolment_ignores_completed_records_for_capacity():
    section = SectionFactory(capacity=1)
    Enrolment.objects.create(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
        status=Enrolment.EnrolmentStatus.COMPLETED,
    )

    enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    assert enrolment.status == Enrolment.EnrolmentStatus.ACTIVE


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


def test_change_section_rejects_full_target_section_without_closing_current_enrolment():
    current_section = SectionFactory()
    target_section = SectionFactory(
        academic_cycle=current_section.academic_cycle,
        grade=current_section.grade,
        shift=current_section.shift,
        capacity=1,
    )
    current_enrolment = create_enrolment(
        student=StudentFactory(),
        academic_cycle=current_section.academic_cycle,
        grade=current_section.grade,
        section=current_section,
    )
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=target_section.academic_cycle,
        grade=target_section.grade,
        section=target_section,
    )

    with pytest.raises(DomainError, match="Section capacity has been reached"):
        change_section(enrolment=current_enrolment, new_section=target_section)

    current_enrolment.refresh_from_db()
    assert current_enrolment.status == Enrolment.EnrolmentStatus.ACTIVE


def test_reenrol_student_reuses_student_record_and_previous_enrolment():
    previous_section = SectionFactory(name="A")
    target_cycle = AcademicCycleFactory(
        institution=previous_section.academic_cycle.institution,
        starts_on=date(2027, 1, 1),
        ends_on=date(2027, 12, 31),
        status="draft",
    )
    target_section = SectionFactory(
        academic_cycle=target_cycle,
        grade=previous_section.grade,
        shift=previous_section.shift,
        name="B",
    )
    student = StudentFactory()
    previous = create_enrolment(
        student=student,
        academic_cycle=previous_section.academic_cycle,
        grade=previous_section.grade,
        section=previous_section,
    )

    enrolment = reenrol_student(
        student=student,
        academic_cycle=target_cycle,
        grade=target_section.grade,
        shift=target_section.shift,
        section=target_section,
    )

    assert enrolment.student_id == student.id
    assert enrolment.academic_cycle_id == target_cycle.id
    assert student.enrolments.filter(pk=previous.pk).exists()


def test_reenrol_student_requires_previous_enrolment():
    section = SectionFactory(name="A")

    with pytest.raises(DomainError, match="no previous enrolment"):
        reenrol_student(
            student=StudentFactory(),
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            shift=section.shift,
            section=section,
        )


def test_reenrol_student_rejects_pre_enrolled_student():
    section = SectionFactory(name="A")

    with pytest.raises(DomainError, match="Only active students"):
        reenrol_student(
            student=StudentFactory(status="pre_enrolled"),
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            shift=section.shift,
            section=section,
        )
