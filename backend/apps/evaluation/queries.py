"""Read-side queries for evaluation configuration and grades."""

from django.db.models import Count, Q

from apps.academics.models import (
    AcademicCycle,
    CurriculumPlan,
    Section,
    Subject,
    TeachingAssignment,
)
from apps.academics.queries import current_teaching_assignment, resolve_institution
from apps.enrolments.models import Enrolment
from apps.evaluation.models import CaptureExceptionGrant, EvaluationUnit, Grade

#: Precarga de una nota para serializarla con nombres sin una consulta por fila.
GRADE_RELATED = (
    "enrolment__student__person",
    "subject",
    "evaluation_unit",
)


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


def grades(
    *,
    cycle_public_id,
    unit_public_id,
    assignments,
    section_id=None,
    subject_id=None,
    student_id=None,
):
    """
    Notas de una unidad, con nombres precargados (V2 de docs/ux-ui.md 2.11).

    ``section_id``, ``subject_id`` y ``student_id`` son public_id opcionales;
    un identificador que no existe deja el listado vacío. El alcance del
    docente (RF-CAL-006) se aplica igual que antes.
    """
    queryset = (
        Grade.objects.filter(
            evaluation_unit__public_id=unit_public_id,
            evaluation_unit__academic_cycle__public_id=cycle_public_id,
            is_active=True,
        )
        .select_related(*GRADE_RELATED)
        .order_by(
            "enrolment__student__person__last_name",
            "enrolment__student__person__first_name",
            "subject__name",
            "pk",
        )
    )
    if section_id:
        queryset = queryset.filter(enrolment__section__public_id=section_id)
    if subject_id:
        queryset = queryset.filter(subject__public_id=subject_id)
    if student_id:
        queryset = queryset.filter(enrolment__student__public_id=student_id)
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


def capture_progress_rows(*, evaluation_unit, pairs=None):
    """
    One row per (section, subarea) of the cycle's curriculum plan for
    ``evaluation_unit`` (RF-CAL-008): how many of the section's active
    enrolments already have a grade for that subarea in this unit, how many are
    still pending, and the teacher currently responsible (the open-ended
    TeachingAssignment, or None when the subarea has no assignment yet).

    Sections with no active enrolment are skipped: there is nothing to capture.
    ``pairs`` (a set of ``(section_id, subject_id)``) keeps only those rows; a
    teacher sees just the sections and subareas assigned to them.

    A fixed number of queries whatever the size of the cycle: plans, sections
    with their active-enrolment count, graded counts grouped by section and
    subarea, and current assignments are each read once and joined in memory.
    """
    cycle = evaluation_unit.academic_cycle
    plans = list(
        CurriculumPlan.objects.filter(academic_cycle=cycle, is_active=True).select_related(
            "grade", "subject"
        )
    )
    sections_by_grade = {}
    sections = (
        Section.objects.filter(offering__academic_cycle=cycle, is_active=True)
        .select_related("offering__grade")
        .annotate(
            active_total=Count(
                "enrolments",
                filter=Q(
                    enrolments__status=Enrolment.EnrolmentStatus.ACTIVE,
                    enrolments__is_active=True,
                ),
            )
        )
    )
    for section in sections:
        sections_by_grade.setdefault(section.offering.grade_id, []).append(section)

    graded = {
        (row["enrolment__section_id"], row["subject_id"]): row["total"]
        for row in Grade.objects.filter(evaluation_unit=evaluation_unit, is_active=True)
        .values("enrolment__section_id", "subject_id")
        .annotate(total=Count("pk"))
    }
    teachers = {
        (assignment.section_id, assignment.subject_id): assignment.teacher
        for assignment in TeachingAssignment.objects.filter(
            academic_cycle=cycle, ends_on__isnull=True
        ).select_related("teacher")
    }

    rows = []
    for plan in plans:
        for section in sections_by_grade.get(plan.grade_id, []):
            key = (section.pk, plan.subject_id)
            if pairs is not None and key not in pairs:
                continue
            total = section.active_total
            if total == 0:
                continue
            count = graded.get(key, 0)
            rows.append(
                {
                    "section": section,
                    "subject": plan.subject,
                    "teacher": teachers.get(key),
                    "students_total": total,
                    "students_graded": count,
                    "students_pending": total - count,
                    "progress_pct": round(count / total * 100, 2),
                }
            )
    return rows


def current_teacher(*, academic_cycle, section, subject):
    """
    Persona docente de la asignación vigente de ``section`` y ``subject``, o
    None (V8 de docs/ux-ui.md 2.11). Reutiliza la consulta de academics.
    """
    assignment = current_teaching_assignment(
        academic_cycle=academic_cycle, section=section, subject=subject
    )
    return assignment.teacher if assignment is not None else None


def institution():
    """La institución sobre la que opera el sistema (configuración global)."""
    return resolve_institution()


def teacher_assignment_pairs(*, assignments, academic_cycle):
    """``(section_id, subject_id)`` of ``assignments`` in ``academic_cycle``."""
    return set(
        assignments.filter(academic_cycle=academic_cycle).values_list("section_id", "subject_id")
    )


def section_in_cycle_or_none(*, academic_cycle, public_id):
    return (
        Section.objects.filter(
            public_id=public_id, offering__academic_cycle=academic_cycle, is_active=True
        )
        .select_related("offering__grade", "offering__academic_cycle__institution")
        .first()
    )


def active_section_enrolments(section):
    """
    Active enrolments of ``section``, ordered by the student's name (apellido,
    nombre). Backs the grade sheet, the section's recovery list and the
    per-row validation of bulk capture.
    """
    return (
        Enrolment.objects.filter(
            section=section,
            status=Enrolment.EnrolmentStatus.ACTIVE,
            is_active=True,
        )
        .select_related("student__person")
        .order_by("student__person__last_name", "student__person__first_name", "pk")
    )


def unit_grades_by_enrolment(*, evaluation_unit, subject, enrolments):
    """``{enrolment_id: Grade}`` of ``subject`` in the unit for those enrolments."""
    return {
        grade.enrolment_id: grade
        for grade in Grade.objects.filter(
            evaluation_unit=evaluation_unit,
            subject=subject,
            enrolment__in=enrolments,
            is_active=True,
        )
    }


def grades_for_enrolment(enrolment):
    """
    All registered grades for one enrolment, across subjects and units
    (RF-CAL-007). Scoped to a single enrolment on purpose: this backs the
    student/guardian portal, which must never expose a section-wide,
    comparative listing.
    """
    return (
        Grade.objects.filter(enrolment=enrolment, is_active=True)
        .select_related(*GRADE_RELATED)
        .order_by("evaluation_unit__number", "subject__name")
    )
