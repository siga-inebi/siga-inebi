from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.academics.cycle_policies import require_cycle_academic_writes
from apps.academics.models import Section
from apps.audit.services import record_event
from apps.common.db import unique_violation_as
from apps.common.models import DomainError
from apps.enrolments.models import Enrolment, EnrolmentDocumentRequirement


def section_occupancy(*, academic_cycle=None, grade=None, section=None, include_inactive=False):
    """
    Declared capacity and real-time occupancy per section (RF-EST-008).

    Annotates ``_active_enrolments`` so ``Section.active_enrolment_count`` and
    ``Section.available_seats`` read the annotation instead of one query per
    row (see the property docstrings in ``apps.academics.models.Section``).
    Filters are all optional; passing none of them lists every section.
    """
    queryset = Section.objects.select_related(
        "offering__grade__level", "offering__shift", "offering__academic_cycle"
    ).annotate(
        _active_enrolments=Count(
            "enrolments", filter=Q(enrolments__status=Enrolment.EnrolmentStatus.ACTIVE)
        )
    )
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    if academic_cycle is not None:
        queryset = queryset.filter(offering__academic_cycle=academic_cycle)
    if grade is not None:
        queryset = queryset.filter(offering__grade=grade)
    if section is not None:
        queryset = queryset.filter(pk=section.pk)
    return queryset.order_by(
        "offering__grade__level__sequence", "offering__grade__sequence", "name"
    )


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


def active_enrolments(*, student=None):
    queryset = (
        Enrolment.objects.filter(is_active=True, status=Enrolment.EnrolmentStatus.ACTIVE)
        .select_related("student", "academic_cycle", "grade", "section")
        .order_by("student__student_code", "effective_on", "pk")
    )
    return queryset.filter(student=student) if student is not None else queryset


def enrolment_history(*, student):
    return (
        Enrolment.objects.filter(student=student)
        .select_related("student", "academic_cycle", "grade", "section")
        .order_by("-effective_on", "-created_at", "-pk")
    )


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
    if student.status != student.StudentStatus.PRE_ENROLLED or not student.is_active:
        raise DomainError("Only pre-enrolled students can be reenrolled.")

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
    student.status = student.StudentStatus.ACTIVE
    student.save(update_fields=["status", "updated_at"])
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


@transaction.atomic
def set_document_requirement(
    *,
    enrolment,
    code,
    name,
    status=None,
    is_required=None,
    actor=None,
):
    if enrolment.academic_cycle.status == enrolment.academic_cycle.CycleStatus.CLOSED:
        raise DomainError("Closed academic cycles do not allow document changes.")

    code = code.strip().upper()
    name = name.strip()
    if not code:
        raise DomainError("Document code cannot be empty.")
    if not name:
        raise DomainError("Document name cannot be empty.")
    if status is not None and status not in EnrolmentDocumentRequirement.DeliveryStatus.values:
        raise DomainError("Invalid document delivery status.")

    # Only overwrite what the caller actually supplied: a partial update must not
    # reset the delivery state. On creation the model defaults fill the rest.
    defaults = {"name": name, "is_active": True}
    if status is not None:
        defaults["status"] = status
    if is_required is not None:
        defaults["is_required"] = is_required

    requirement, created = EnrolmentDocumentRequirement.objects.update_or_create(
        enrolment=enrolment,
        code=code,
        defaults=defaults,
    )
    record_event(
        actor=actor,
        action=(
            "enrolments.document_requirement.created"
            if created
            else "enrolments.document_requirement.updated"
        ),
        resource="EnrolmentDocumentRequirement",
        resource_identifier=str(requirement.pk),
        context={"enrolment_id": enrolment.pk, "code": code, "status": requirement.status},
    )
    return requirement


def pending_required_document_codes(*, enrolment):
    """Return the codes of active, required documents not yet delivered."""
    return list(
        EnrolmentDocumentRequirement.objects.filter(
            enrolment=enrolment, is_active=True, is_required=True
        )
        .exclude(status=EnrolmentDocumentRequirement.DeliveryStatus.DELIVERED)
        .values_list("code", flat=True)
    )
