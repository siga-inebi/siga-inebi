"""Read-side queries for evaluation configuration and grades."""

from django.db.models import Q

from apps.academics.models import AcademicCycle, Subject
from apps.enrolments.models import Enrolment
from apps.evaluation.models import CaptureExceptionGrant, EvaluationUnit, Grade


def evaluation_units(cycle_public_id):
    if not cycle_public_id:
        return EvaluationUnit.objects.none()
    return EvaluationUnit.objects.filter(
        academic_cycle__public_id=cycle_public_id,
        is_active=True,
    ).order_by("number")


def academic_cycle_or_none(public_id):
    return AcademicCycle.objects.filter(public_id=public_id).first()


def evaluation_unit_or_none(*, cycle_public_id, unit_public_id):
    return EvaluationUnit.objects.filter(
        public_id=unit_public_id,
        academic_cycle__public_id=cycle_public_id,
        is_active=True,
    ).first()


def capture_exception_grants(*, cycle_public_id, unit_public_id):
    return CaptureExceptionGrant.objects.filter(
        evaluation_unit__public_id=unit_public_id,
        evaluation_unit__academic_cycle__public_id=cycle_public_id,
        is_active=True,
    )


def grades(*, cycle_public_id, unit_public_id, assignments):
    queryset = Grade.objects.filter(
        evaluation_unit__public_id=unit_public_id,
        evaluation_unit__academic_cycle__public_id=cycle_public_id,
        is_active=True,
    )
    pairs = list(assignments.values_list("section_id", "subject_id"))
    if not pairs:
        return queryset

    scope = Q(pk__in=[])
    for section_id, subject_id in pairs:
        scope |= Q(enrolment__section_id=section_id, subject_id=subject_id)
    return queryset.filter(scope)


def enrolment_or_none(*, cycle_public_id, enrolment_id):
    return Enrolment.objects.filter(
        public_id=enrolment_id,
        academic_cycle__public_id=cycle_public_id,
        is_active=True,
    ).first()


def subject_or_none(public_id):
    return Subject.objects.filter(public_id=public_id, is_active=True).first()


def grades_for_enrolment(enrolment):
    """
    All registered grades for one enrolment, across subjects and units
    (RF-CAL-007). Scoped to a single enrolment on purpose: this backs the
    student/guardian portal, which must never expose a section-wide,
    comparative listing.
    """
    return (
        Grade.objects.filter(enrolment=enrolment, is_active=True)
        .select_related("subject", "evaluation_unit")
        .order_by("evaluation_unit__number", "subject__name")
    )
