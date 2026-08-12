from datetime import timedelta

import pytest
from django.utils import timezone

from apps.common.models import DomainError
from apps.enrolments.services import change_section, create_enrolment
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
    first_section = SectionFactory()
    second_section = SectionFactory(
        academic_cycle=first_section.academic_cycle,
        grade=first_section.grade,
        shift=first_section.shift,
        name="Z",
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
