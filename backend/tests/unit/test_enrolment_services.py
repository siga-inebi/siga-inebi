import pytest
from django.utils import timezone

from apps.academics.models import AcademicCycle
from apps.common.models import DomainError
from apps.enrolments.models import Enrolment
from apps.enrolments.services import create_enrolment, reenrol, withdraw
from tests.factories.academic import AcademicCycleFactory, SectionFactory
from tests.factories.students import StudentFactory

# ---------------------------------------------------------------------------
# create_enrolment — capacity guard (RF-MAT-004)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.django_db
def test_create_enrolment_succeeds_within_capacity():
    section = SectionFactory(capacity=2)
    student = StudentFactory()

    enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    assert enrolment.status == Enrolment.EnrolmentStatus.ACTIVE


@pytest.mark.unit
@pytest.mark.django_db
def test_create_enrolment_rejects_when_section_full():
    section = SectionFactory(capacity=1)
    existing_student = StudentFactory()
    create_enrolment(
        student=existing_student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    new_student = StudentFactory()
    with pytest.raises(DomainError, match="capacity"):
        create_enrolment(
            student=new_student,
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            section=section,
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_create_enrolment_ignores_non_active_enrolments_for_capacity():
    """Withdrawn/completed enrolments do not count toward capacity."""
    section = SectionFactory(capacity=1)
    old_student = StudentFactory()
    enrolment = create_enrolment(
        student=old_student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    enrolment.status = Enrolment.EnrolmentStatus.WITHDRAWN
    enrolment.save(update_fields=["status", "updated_at"])

    new_student = StudentFactory()
    result = create_enrolment(
        student=new_student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    assert result.status == Enrolment.EnrolmentStatus.ACTIVE


@pytest.mark.unit
@pytest.mark.django_db
def test_create_enrolment_rejects_closed_cycle():
    section = SectionFactory()
    section.academic_cycle.status = AcademicCycle.CycleStatus.CLOSED
    section.academic_cycle.save(update_fields=["status", "updated_at"])
    student = StudentFactory()

    with pytest.raises(DomainError, match="Closed"):
        create_enrolment(
            student=student,
            academic_cycle=section.academic_cycle,
            grade=section.grade,
            section=section,
        )


# ---------------------------------------------------------------------------
# withdraw (RF-MOV-004)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.django_db
def test_withdraw_sets_withdrawn_status():
    section = SectionFactory()
    student = StudentFactory()
    enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    withdraw(enrolment=enrolment, reason="Family relocation")
    enrolment.refresh_from_db()

    assert enrolment.status == Enrolment.EnrolmentStatus.WITHDRAWN
    assert enrolment.ends_on is not None


@pytest.mark.unit
@pytest.mark.django_db
def test_withdraw_accepts_explicit_effective_date():
    section = SectionFactory()
    student = StudentFactory()
    enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    effective = timezone.localdate()

    withdraw(enrolment=enrolment, reason="Transfer", effective_on=effective)
    enrolment.refresh_from_db()

    assert enrolment.ends_on == effective


@pytest.mark.unit
@pytest.mark.django_db
def test_withdraw_rejects_non_active_enrolment():
    section = SectionFactory()
    student = StudentFactory()
    enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    withdraw(enrolment=enrolment, reason="First withdrawal")

    with pytest.raises(DomainError, match="active"):
        withdraw(enrolment=enrolment, reason="Duplicate attempt")


@pytest.mark.unit
@pytest.mark.django_db
def test_withdraw_rejects_closed_cycle():
    section = SectionFactory()
    student = StudentFactory()
    enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    enrolment.academic_cycle.status = AcademicCycle.CycleStatus.CLOSED
    enrolment.academic_cycle.save(update_fields=["status", "updated_at"])

    with pytest.raises(DomainError, match="closed"):
        withdraw(enrolment=enrolment, reason="Should fail")


# ---------------------------------------------------------------------------
# reenrol (RF-MAT-003)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.django_db
def test_reenrol_creates_new_enrolment_in_new_cycle():
    section = SectionFactory()
    student = StudentFactory()
    old_enrolment = create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )
    old_enrolment.status = Enrolment.EnrolmentStatus.COMPLETED
    old_enrolment.save(update_fields=["status", "updated_at"])

    new_cycle = AcademicCycleFactory(
        institution=section.academic_cycle.institution,
        status=AcademicCycle.CycleStatus.ACTIVE,
    )
    new_section = SectionFactory(academic_cycle=new_cycle, grade=section.grade)

    new_enrolment = reenrol(
        student=student,
        new_cycle=new_cycle,
        new_grade=section.grade,
        new_section=new_section,
    )

    assert new_enrolment.student == student
    assert new_enrolment.academic_cycle == new_cycle
    assert new_enrolment.status == Enrolment.EnrolmentStatus.ACTIVE


@pytest.mark.unit
@pytest.mark.django_db
def test_reenrol_rejects_when_new_cycle_is_closed():
    section = SectionFactory()
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    closed_cycle = AcademicCycleFactory(
        institution=section.academic_cycle.institution,
        status=AcademicCycle.CycleStatus.CLOSED,
    )
    new_section = SectionFactory(academic_cycle=closed_cycle, grade=section.grade)

    with pytest.raises(DomainError, match="Closed"):
        reenrol(
            student=student,
            new_cycle=closed_cycle,
            new_grade=section.grade,
            new_section=new_section,
        )


@pytest.mark.unit
@pytest.mark.django_db
def test_reenrol_rejects_duplicate_active_enrolment_in_new_cycle():
    section = SectionFactory()
    student = StudentFactory()
    create_enrolment(
        student=student,
        academic_cycle=section.academic_cycle,
        grade=section.grade,
        section=section,
    )

    # Attempt to re-enrol in the same active cycle
    with pytest.raises(DomainError, match="already enrolled"):
        reenrol(
            student=student,
            new_cycle=section.academic_cycle,
            new_grade=section.grade,
            new_section=section,
        )
