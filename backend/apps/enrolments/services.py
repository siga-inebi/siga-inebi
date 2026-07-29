from django.utils import timezone

from apps.audit.services import record_event
from apps.common.models import DomainError
from apps.enrolments.models import Enrolment


def create_enrolment(
    *,
    student,
    academic_cycle,
    grade,
    section,
    actor=None,
    effective_on=None,
):
    if academic_cycle.status == academic_cycle.CycleStatus.CLOSED:
        raise DomainError("Closed academic cycles do not accept enrolment changes.")

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


def change_section(*, enrolment, new_section, actor=None, effective_on=None):
    if enrolment.academic_cycle.status == enrolment.academic_cycle.CycleStatus.CLOSED:
        raise DomainError("Closed academic cycles do not allow section changes.")

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
