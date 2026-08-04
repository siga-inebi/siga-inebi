from django.db import transaction
from django.utils import timezone

from apps.academics.services import locked_occupancy
from apps.audit.services import record_event
from apps.common.models import DomainError
from apps.enrolments.models import Enrolment


def _check_capacity(section):
    """
    Raise DomainError if section has reached its declared capacity.
    Only ACTIVE enrolments count toward capacity (RF-MAT-004, RF-EST-008).

    The section row is locked before counting: this is a read-then-write
    decision, so without the lock two concurrent enrolments both see the same
    count and together push occupancy past the declared capacity.
    """
    if section.capacity == 0:
        # capacity == 0 means uncapped (e.g. during initial setup)
        return

    active_count = locked_occupancy(section)

    if active_count >= section.capacity:
        raise DomainError(
            f"Section '{section.name}' has reached its capacity of {section.capacity} students."
        )


def _check_catalogue_consistency(section, academic_cycle, grade):
    """
    The section is the leaf of a grade offering, so it already knows its cycle
    and grade. Refuse payloads where the three do not agree instead of storing a
    contradictory enrolment.
    """
    offering = section.offering

    if offering.academic_cycle_id != academic_cycle.pk:
        raise DomainError(
            f"Section '{section.name}' does not belong to cycle '{academic_cycle.name}'."
        )

    if offering.grade_id != grade.pk:
        raise DomainError(f"Section '{section.name}' does not belong to grade '{grade.name}'.")


@transaction.atomic
def create_enrolment(
    *,
    student,
    academic_cycle,
    grade,
    section,
    actor=None,
    effective_on=None,
):
    """
    Inscribe a student in a cycle/grade/section (RF-MAT-001, RF-MAT-002).
    """
    if academic_cycle.status == academic_cycle.CycleStatus.CLOSED:
        raise DomainError("Closed academic cycles do not accept enrolment changes.")

    _check_catalogue_consistency(section, academic_cycle, grade)
    _check_capacity(section)

    enrolment = Enrolment.objects.create(
        student=student,
        academic_cycle=academic_cycle,
        grade=grade,
        section=section,
        effective_on=effective_on or timezone.localdate(),
    )
    record_event(
        actor=actor,
        action="enrolments.enrolment.created",
        resource="Enrolment",
        resource_identifier=str(enrolment.pk),
        context={"student_id": student.pk, "section_id": section.pk},
    )
    return enrolment


@transaction.atomic
def change_section(*, enrolment, new_section, actor=None, effective_on=None):
    """
    Move a student to a different section within the same cycle (RF-MOV-001, RF-MOV-002).
    Previous enrolment is closed as COMPLETED; a new one is created.
    """
    if enrolment.academic_cycle.status == enrolment.academic_cycle.CycleStatus.CLOSED:
        raise DomainError("Closed academic cycles do not allow section changes.")

    _check_catalogue_consistency(new_section, enrolment.academic_cycle, enrolment.grade)
    _check_capacity(new_section)

    effective_on = effective_on or timezone.localdate()
    enrolment.status = Enrolment.EnrolmentStatus.COMPLETED
    enrolment.ends_on = effective_on
    enrolment.save(update_fields=["status", "ends_on", "updated_at"])

    replacement = Enrolment.objects.create(
        student=enrolment.student,
        academic_cycle=enrolment.academic_cycle,
        grade=enrolment.grade,
        section=new_section,
        effective_on=effective_on,
        status=Enrolment.EnrolmentStatus.ACTIVE,
    )
    record_event(
        actor=actor,
        action="enrolments.enrolment.section_changed",
        resource="Enrolment",
        resource_identifier=str(replacement.pk),
        context={
            "previous_enrolment_id": enrolment.pk,
            "new_section_id": new_section.pk,
        },
    )
    return replacement


def withdraw(*, enrolment, reason, actor=None, effective_on=None):
    """
    Withdraw a student from a cycle (RF-MOV-004).

    - Only ACTIVE enrolments can be withdrawn.
    - Closed cycles do not allow withdrawals.
    - History is preserved; the record is not deleted.
    """
    if enrolment.status != Enrolment.EnrolmentStatus.ACTIVE:
        raise DomainError(
            f"Only active enrolments can be withdrawn. Current status: '{enrolment.status}'."
        )

    if enrolment.academic_cycle.status == enrolment.academic_cycle.CycleStatus.CLOSED:
        raise DomainError("Cannot withdraw from a closed academic cycle.")

    effective_on = effective_on or timezone.localdate()
    enrolment.status = Enrolment.EnrolmentStatus.WITHDRAWN
    enrolment.ends_on = effective_on
    enrolment.save(update_fields=["status", "ends_on", "updated_at"])

    record_event(
        actor=actor,
        action="enrolments.enrolment.withdrawn",
        resource="Enrolment",
        resource_identifier=str(enrolment.pk),
        context={
            "student_id": enrolment.student_id,
            "reason": reason,
            "effective_on": str(effective_on),
        },
    )
    return enrolment


def reenrol(*, student, new_cycle, new_grade, new_section, actor=None, effective_on=None):
    """
    Re-enrol a student in a new cycle (RF-MAT-003).

    - The caller is responsible for resolving grade (promoted or repeating).
    - Verifies the student is not already actively enrolled in new_cycle.
    - Delegates capacity check to create_enrolment.
    """
    already_enrolled = Enrolment.objects.filter(
        student=student,
        academic_cycle=new_cycle,
        status=Enrolment.EnrolmentStatus.ACTIVE,
    ).exists()

    if already_enrolled:
        raise DomainError(f"Student is already enrolled in cycle '{new_cycle.name}'.")

    return create_enrolment(
        student=student,
        academic_cycle=new_cycle,
        grade=new_grade,
        section=new_section,
        actor=actor,
        effective_on=effective_on,
    )
