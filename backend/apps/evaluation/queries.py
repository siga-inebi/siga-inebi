"""Read-side queries for evaluation configuration and grades."""

from django.db.models import Count, Q

from apps.academics.models import (
    AcademicCycle,
    CurriculumPlan,
    Section,
    Subject,
    TeachingAssignment,
)
from apps.academics.models import Grade as AcademicGrade
from apps.academics.queries import current_teaching_assignment, resolve_institution
from apps.enrolments.models import Enrolment
from apps.evaluation.models import CaptureExceptionGrant, EvaluationUnit, Grade
from apps.students.models import Student

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


# --------------------------------------------------------------------------- #
# Notas por curso (plantilla Excel) e informe de calificaciones
# --------------------------------------------------------------------------- #


def cycle_course_pairs(academic_cycle):
    """
    Every ``(section, subject)`` the cycle's curriculum plan expects: each
    active section crossed with the subjects of its grade's active plan. Backs
    the course list of an institution-wide grade writer. Two queries, whatever
    the number of sections.
    """
    sections = list(
        Section.objects.filter(offering__academic_cycle=academic_cycle, is_active=True)
        .select_related("offering__grade__level", "offering__shift")
        .order_by("offering__grade__level__sequence", "offering__grade__sequence", "name", "pk")
    )
    subjects_by_grade = {}
    for plan in (
        CurriculumPlan.objects.filter(academic_cycle=academic_cycle, is_active=True)
        .select_related("subject")
        .order_by("subject__name")
    ):
        subjects_by_grade.setdefault(plan.grade_id, []).append(plan.subject)
    return [
        (section, subject)
        for section in sections
        for subject in subjects_by_grade.get(section.offering.grade_id, [])
    ]


def assignment_course_pairs(assignments, academic_cycle):
    """``(section, subject)`` of a teacher's ``assignments`` in ``academic_cycle``, ordered."""
    rows = (
        assignments.filter(academic_cycle=academic_cycle, section__is_active=True)
        .select_related("section__offering__grade__level", "section__offering__shift", "subject")
        .order_by(
            "section__offering__grade__level__sequence",
            "section__offering__grade__sequence",
            "section__name",
            "subject__name",
        )
    )
    seen = set()
    pairs = []
    for assignment in rows:
        key = (assignment.section_id, assignment.subject_id)
        if key not in seen:
            seen.add(key)
            pairs.append((assignment.section, assignment.subject))
    return pairs


def current_teachers_by_pair(academic_cycle):
    """``{(section_id, subject_id): Person}`` of the cycle's current assignments, one query."""
    return {
        (assignment.section_id, assignment.subject_id): assignment.teacher
        for assignment in TeachingAssignment.objects.filter(
            academic_cycle=academic_cycle, ends_on__isnull=True, is_active=True
        ).select_related("teacher")
    }


def active_cycle_units(academic_cycle):
    """Active evaluation units of the cycle, in order. Their count is configuration, not fixed."""
    return list(
        EvaluationUnit.objects.filter(academic_cycle=academic_cycle, is_active=True).order_by(
            "number"
        )
    )


def course_grades(*, section, subject, units):
    """``{(enrolment_id, unit_id): Grade}`` of one course across ``units``, one query."""
    return {
        (grade.enrolment_id, grade.evaluation_unit_id): grade
        for grade in Grade.objects.filter(
            enrolment__section=section,
            subject=subject,
            evaluation_unit__in=units,
            is_active=True,
        )
    }


def active_capture_exception_unit_ids(*, units, subject, teacher, at):
    """Ids of ``units`` where an unexpired exceptional grant covers ``teacher`` and ``subject``."""
    return set(
        CaptureExceptionGrant.objects.filter(
            evaluation_unit__in=units,
            subject=subject,
            teacher=teacher,
            is_active=True,
            expires_at__gt=at,
        ).values_list("evaluation_unit_id", flat=True)
    )


def report_enrolments(*, academic_cycle, grade=None, section=None, student=None):
    """
    Active enrolments the grade report covers, ordered by grade, section and
    student name. Filters narrow from the whole cycle to a grade, a section or
    one student. One query.
    """
    queryset = Enrolment.objects.filter(
        academic_cycle=academic_cycle,
        status=Enrolment.EnrolmentStatus.ACTIVE,
        is_active=True,
    )
    if section is not None:
        queryset = queryset.filter(section=section)
    elif grade is not None:
        queryset = queryset.filter(section__offering__grade=grade)
    if student is not None:
        queryset = queryset.filter(student=student)
    return queryset.select_related(
        "student__person", "section__offering__grade__level", "section__offering__shift"
    ).order_by(
        "section__offering__grade__level__sequence",
        "section__offering__grade__sequence",
        "section__name",
        "student__person__last_name",
        "student__person__first_name",
        "pk",
    )


def plan_subjects_by_grade(academic_cycle, grade_ids):
    """``{grade_id: [(subject_id, name), ...]}`` from the cycle's active plans, one query."""
    result = {}
    for grade_id, subject_id, name in (
        CurriculumPlan.objects.filter(
            academic_cycle=academic_cycle, grade_id__in=grade_ids, is_active=True
        )
        .order_by("subject__name")
        .values_list("grade_id", "subject_id", "subject__name")
    ):
        result.setdefault(grade_id, []).append((subject_id, name))
    return result


def report_grade_values(*, enrolment_ids, unit_ids):
    """
    ``(enrolment_id, subject_id, subject_name, unit_id, value)`` tuples for the
    report. Plain tuples, not model instances: the report reads thousands of
    grades and needs only these values. Chunked so the IN list stays bounded.
    """
    chunk_size = 1000
    for start in range(0, len(enrolment_ids), chunk_size):
        yield from Grade.objects.filter(
            enrolment_id__in=enrolment_ids[start : start + chunk_size],
            evaluation_unit_id__in=unit_ids,
            is_active=True,
        ).values_list("enrolment_id", "subject_id", "subject__name", "evaluation_unit_id", "value")


def grade_in_institution_or_none(*, institution, public_id):
    return (
        AcademicGrade.objects.filter(level__institution=institution, public_id=public_id)
        .select_related("level")
        .first()
    )


def student_or_none(public_id):
    return Student.objects.filter(public_id=public_id).select_related("person").first()
