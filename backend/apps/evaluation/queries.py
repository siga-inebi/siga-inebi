"""Read-side queries for evaluation configuration and grades."""

from django.db.models import Q

from apps.academics.models import (
    AcademicCycle,
    CurriculumPlan,
    Section,
    Subject,
    TeachingAssignment,
)
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


def curriculum_subjects(academic_cycle, grade):
    """
    Subareas in the grade's curriculum plan for the cycle (RF-EST-005).

    Backs the recovery-eligibility check (RF-RES-004): both the total count and
    the set of subareas whose final grade must be inspected come from here, so
    the failed-subarea limit is derived from the plan and never a fixed number.
    """
    return (
        Subject.objects.filter(
            curriculum_plans__academic_cycle=academic_cycle,
            curriculum_plans__grade=grade,
            curriculum_plans__is_active=True,
        )
        .distinct()
        .order_by("name")
    )


def capture_progress_rows(*, evaluation_unit):
    """
    One row per (section, subarea) of the cycle's curriculum plan for
    ``evaluation_unit`` (RF-CAL-008): how many of the section's active
    enrolments already have a grade for that subarea in this unit, how many are
    still pending, and the teacher currently responsible (the open-ended
    TeachingAssignment, or None when the subarea has no assignment yet).

    Sections with no active enrolment are skipped: there is nothing to capture.
    """
    cycle = evaluation_unit.academic_cycle
    plans = CurriculumPlan.objects.filter(academic_cycle=cycle, is_active=True).select_related(
        "grade", "subject"
    )

    rows = []
    for plan in plans:
        sections = Section.objects.filter(
            offering__academic_cycle=cycle,
            offering__grade=plan.grade,
            is_active=True,
        ).select_related("offering__grade")
        for section in sections:
            total = Enrolment.objects.filter(
                section=section,
                status=Enrolment.EnrolmentStatus.ACTIVE,
                is_active=True,
            ).count()
            if total == 0:
                continue
            graded = Grade.objects.filter(
                evaluation_unit=evaluation_unit,
                subject=plan.subject,
                enrolment__section=section,
                is_active=True,
            ).count()
            assignment = (
                TeachingAssignment.objects.filter(
                    academic_cycle=cycle,
                    section=section,
                    subject=plan.subject,
                    ends_on__isnull=True,
                )
                .select_related("teacher")
                .first()
            )
            rows.append(
                {
                    "section": section,
                    "subject": plan.subject,
                    "teacher": assignment.teacher if assignment is not None else None,
                    "students_total": total,
                    "students_graded": graded,
                    "students_pending": total - graded,
                    "progress_pct": round(graded / total * 100, 2),
                }
            )
    return rows


def active_enrolment_in_section(*, section, student_code):
    """
    The active enrolment of the student with ``student_code`` in ``section``,
    or None. Backs per-row validation of the bulk grade upload (RF-CAL-004):
    "the student exists and belongs to the section" is a single check here.
    """
    return (
        Enrolment.objects.filter(
            section=section,
            student__student_code=student_code,
            status=Enrolment.EnrolmentStatus.ACTIVE,
            is_active=True,
        )
        .select_related("student")
        .first()
    )


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
