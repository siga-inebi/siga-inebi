from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.common.models import DomainError
from apps.enrolments.services import (
    change_section,
    create_enrolment,
    matriculate_student,
    reenrol_student,
)
from tests.factories.academic import AcademicCycleFactory, SectionFactory
from tests.factories.students import StudentFactory


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_create_valid_enrolment():
    section = SectionFactory()
    student = StudentFactory()

    enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    assert enrolment.status == enrolment.EnrolmentStatus.ACTIVE


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_cannot_duplicate_incompatible_active_enrolment():
    section = SectionFactory()
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    with pytest.raises(DomainError, match="already has an active enrolment"):
        create_enrolment(
            student=student,
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            section=section,
        )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_change_section_keeps_history():
    first_section = SectionFactory(name="A")
    second_section = SectionFactory(
        academic_cycle=first_section.academic_cycle,
        grade=first_section.grade,
        shift=first_section.shift,
        name="Replacement",
    )
    student = StudentFactory()
    enrolment = create_enrolment(
        student=student,
        academic_cycle=first_section.academic_cycle,
        grade=first_section.grade,
        section=first_section,
    )

    replacement = change_section(
        enrolment=enrolment,
        new_section=second_section,
        effective_on=timezone.localdate(),
    )

    enrolment.refresh_from_db()
    assert enrolment.status == enrolment.EnrolmentStatus.COMPLETED
    assert replacement.section_id == second_section.id
    assert student.enrolments.count() == 2


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_closed_cycle_blocks_changes():
    cycle = AcademicCycleFactory(status="closed")
    section = SectionFactory(academic_cycle=cycle)
    student = StudentFactory()

    with pytest.raises(DomainError):
        create_enrolment(
            student=student,
            academic_cycle=cycle,
            grade=section.grade,
            section=section,
        )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_create_enrolment_rejects_section_from_another_cycle():
    section = SectionFactory()
    other_section = SectionFactory()
    student = StudentFactory()

    with pytest.raises(DomainError, match="Section must belong to the academic cycle"):
        create_enrolment(
            student=student,
            academic_cycle=section.academic_cycle,
            grade=other_section.grade,
            section=other_section,
        )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_create_enrolment_rejects_end_date_before_effective_date():
    section = SectionFactory()
    student = StudentFactory()

    with pytest.raises(DomainError, match="end date cannot precede"):
        create_enrolment(
            student=student,
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            section=section,
            effective_on=timezone.localdate(),
            ends_on=timezone.localdate() - timedelta(days=1),
        )


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_matriculation_crosses_student_and_academic_domains():
    section = SectionFactory()
    student = StudentFactory(status="pre_enrolled")

    enrolment = matriculate_student(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        shift=section.shift,
        section=section,
    )

    student.refresh_from_db()
    assert enrolment.student_id == student.id
    assert enrolment.section_id == section.id
    assert enrolment.section.shift.id == section.shift.id
    assert student.status == student.StudentStatus.ACTIVE


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_matriculation_blocks_full_section_and_preserves_student_status():
    section = SectionFactory(capacity=1)
    create_enrolment(
        student=StudentFactory(),
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    student = StudentFactory(status="pre_enrolled")

    with pytest.raises(DomainError, match="Section capacity has been reached"):
        matriculate_student(
            student=student,
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            shift=section.shift,
            section=section,
        )

    student.refresh_from_db()
    assert student.status == student.StudentStatus.PRE_ENROLLED
    assert student.enrolments.count() == 0


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.django_db
def test_reenrolment_crosses_student_and_academic_domains():
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

    current = reenrol_student(
        student=student,
        academic_cycle=target_cycle,
        grade=target_section.grade,
        shift=target_section.shift,
        section=target_section,
    )

    assert current.student_id == previous.student_id
    assert current.academic_cycle_id == target_cycle.id
    assert student.enrolments.count() == 2
