from django.db import transaction
from django.utils import timezone

from apps.academics.cycle_policies import require_cycle_academic_writes
from apps.audit.services import record_event
from apps.common.db import unique_violation_as
from apps.common.models import DomainError
from apps.enrolments.models import Enrolment


def _ensure_section_has_capacity(section):
    locked_section = section.__class__.objects.select_for_update().get(pk=section.pk)
    if locked_section.capacity == 0:
        return

    active_count = Enrolment.objects.filter(
        section=locked_section,
        status=Enrolment.EnrolmentStatus.ACTIVE,
    ).count()
    if active_count >= locked_section.capacity:
        raise DomainError("Section capacity has been reached.")


@transaction.atomic
def create_enrolment(
    *,
    student,
    academic_cycle,
    grade,
    section,
    actor=None,
    effective_on=None,
    ends_on=None,
):
    effective_on = effective_on or timezone.localdate()

    require_cycle_academic_writes(
        cycle=academic_cycle,
        operation="enrolment.create",
    )
    if section.academic_cycle.id != academic_cycle.pk:
        raise DomainError("Section must belong to the academic cycle.")
    if section.grade.id != grade.pk:
        raise DomainError("Section must belong to the grade.")
    if ends_on is not None and effective_on > ends_on:
        raise DomainError("Enrolment end date cannot precede its effective date.")
    _ensure_section_has_capacity(section)

    with unique_violation_as(
        {
            "unique_active_enrolment_per_student_cycle": (
                "Student already has an active enrolment in this academic cycle."
            )
        }
    ):
        enrolment = Enrolment.objects.create(
            student=student,
            academic_cycle=academic_cycle,
            grade=grade,
            section=section,
            effective_on=effective_on,
            ends_on=ends_on,
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
def matriculate_student(
    *, student, academic_cycle, grade, shift, section, actor=None, effective_on=None
):
    """Create the first active enrolment for a pre-enrolled student."""
    if student.status != student.StudentStatus.PRE_ENROLLED:
        raise DomainError("Only pre-enrolled students can be matriculated.")
    if not student.is_active:
        raise DomainError("Inactive students cannot be matriculated.")
    if section.shift.id != shift.pk:
        raise DomainError("Section must belong to the selected shift.")

    enrolment = create_enrolment(
        student=student,
        academic_cycle=academic_cycle,
        grade=grade,
        section=section,
        actor=actor,
        effective_on=effective_on,
    )
    student.status = student.StudentStatus.ACTIVE
    student.save(update_fields=["status", "updated_at"])
    record_event(
        actor=actor,
        action="enrolments.student.matriculated",
        resource="Student",
        resource_identifier=str(student.pk),
        context={
            "enrolment_id": enrolment.pk,
            "academic_cycle_id": academic_cycle.pk,
            "grade_id": grade.pk,
            "shift_id": shift.pk,
            "section_id": section.pk,
        },
    )
    return enrolment


@transaction.atomic
def reenrol_student(
    *, student, academic_cycle, grade, shift, section, actor=None, effective_on=None
):
    """Create a new-cycle enrolment using the student's existing record."""
    if student.status != student.StudentStatus.ACTIVE or not student.is_active:
        raise DomainError("Only active students can be reenrolled.")

    previous = (
        Enrolment.objects.filter(student=student)
        .exclude(academic_cycle=academic_cycle)
        .exclude(status=Enrolment.EnrolmentStatus.CANCELLED)
        .order_by("-effective_on", "-created_at")
        .first()
    )
    if previous is None:
        raise DomainError("Student has no previous enrolment to inherit.")
    if section.shift.id != shift.pk:
        raise DomainError("Section must belong to the selected shift.")

    enrolment = create_enrolment(
        student=student,
        academic_cycle=academic_cycle,
        grade=grade,
        section=section,
        actor=actor,
        effective_on=effective_on,
    )
    record_event(
        actor=actor,
        action="enrolments.student.reenrolled",
        resource="Student",
        resource_identifier=str(student.pk),
        context={
            "enrolment_id": enrolment.pk,
            "previous_enrolment_id": previous.pk,
            "academic_cycle_id": academic_cycle.pk,
        },
    )
    return enrolment


def change_section(*, enrolment, new_section, actor=None, effective_on=None):
    require_cycle_academic_writes(
        cycle=enrolment.academic_cycle,
        operation="enrolment.change_section",
    )
    if new_section.academic_cycle.id != enrolment.academic_cycle_id:
        raise DomainError("Section must belong to the academic cycle.")
    if new_section.grade.id != enrolment.grade_id:
        raise DomainError("Section must belong to the grade.")
    _ensure_section_has_capacity(new_section)

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
