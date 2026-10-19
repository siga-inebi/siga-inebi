"""Read-side queries for the academic-structure domain."""

from django.db.models import Count, OuterRef, Prefetch, Q, Subquery
from django.utils import timezone

from apps.academics.models import (
    AcademicCycle,
    Campus,
    Classroom,
    ClassScheduleBlock,
    ClassSchedulePublication,
    ClassSession,
    CurriculumPlan,
    FrozenPromotionResult,
    FrozenSubjectResult,
    Grade,
    GradeOffering,
    Institution,
    Level,
    LevelSubject,
    NonComputableDay,
    Section,
    Shift,
    Subject,
    TeachingAssignment,
)
from apps.common.exceptions import DomainError, ResourceNotFoundError


def resolve_institution():
    institution = Institution.objects.order_by("pk").first()
    if institution is None:
        raise ResourceNotFoundError("Todavía no hay una institución configurada.")
    return institution


def academic_cycles(institution):
    return AcademicCycle.objects.filter(institution=institution).order_by("-year", "starts_on")


def academic_cycle_or_404(institution, public_id):
    return _get(academic_cycles(institution), public_id, "el ciclo escolar")


def academic_cycle_for_payload(public_id):
    return _get_payload(AcademicCycle.objects.all(), public_id, "el ciclo escolar")


def latest_cycle_year(institution):
    return academic_cycles(institution).values_list("year", flat=True).first()


def _filter_active(queryset, *, include_inactive=False):
    return queryset if include_inactive else queryset.filter(is_active=True)


def campuses_all(institution):
    return (
        Campus.objects.filter(institution=institution)
        .annotate(_shift_count=Count("shifts", filter=Q(shifts__is_active=True), distinct=True))
        .order_by("name")
    )


def campuses(institution, *, include_inactive=False):
    return _filter_active(campuses_all(institution), include_inactive=include_inactive)


def campus_or_404(institution, public_id):
    return _get(campuses_all(institution), public_id, "la sede")


def classrooms(institution, *, include_inactive=False, campus_id=None):
    queryset = Classroom.objects.filter(campus__institution=institution).select_related("campus")
    queryset = _filter_active(queryset, include_inactive=include_inactive)
    if campus_id:
        queryset = queryset.filter(campus__public_id=campus_id)
    return queryset


def classroom_or_404(institution, public_id):
    return _get(
        Classroom.objects.filter(campus__institution=institution).select_related("campus"),
        public_id,
        "Classroom",
    )


def shifts(campus, *, include_inactive=False):
    return _filter_active(
        Shift.objects.filter(campus=campus).select_related("campus"),
        include_inactive=include_inactive,
    )


def shift_or_404(institution, public_id):
    return _get(
        Shift.objects.filter(campus__institution=institution).select_related("campus"),
        public_id,
        "Shift",
    )


def shift_for_payload(institution, public_id):
    return _get_payload(
        Shift.objects.filter(campus__institution=institution), public_id, "la jornada"
    )


def class_schedule_blocks(shift, *, include_inactive=False):
    return _filter_active(
        ClassScheduleBlock.objects.filter(shift=shift).select_related("shift__campus"),
        include_inactive=include_inactive,
    )


def class_schedule_block_or_404(institution, public_id):
    return _get(
        ClassScheduleBlock.objects.filter(shift__campus__institution=institution).select_related(
            "shift__campus"
        ),
        public_id,
        "Class schedule block",
    )


def class_schedule_block_for_payload(institution, public_id):
    return _get_payload(
        ClassScheduleBlock.objects.filter(shift__campus__institution=institution),
        public_id,
        "Class schedule block",
    )


def levels_all(institution):
    return (
        Level.objects.filter(institution=institution)
        .annotate(
            _grade_count=Count("grades", filter=Q(grades__is_active=True), distinct=True),
            _subject_count=Count("level_subjects", distinct=True),
        )
        .order_by("sequence", "name")
    )


def levels(institution, *, include_inactive=False):
    return _filter_active(levels_all(institution), include_inactive=include_inactive)


def level_or_404(institution, public_id):
    return _get(levels_all(institution), public_id, "el nivel")


def grades(level, *, include_inactive=False):
    return _filter_active(
        Grade.objects.filter(level=level).select_related("level"), include_inactive=include_inactive
    )


def grades_for_levels(levels, *, include_inactive=False):
    """
    Grados de varios niveles en una sola consulta.

    Existe para que ``?expand=grades`` en el listado de niveles no dispare una
    consulta por nivel (el N+1 que traia el selector de "Presencia en tiempo
    real"): quien llama agrupa el resultado por ``level_id`` una sola vez.
    """
    return _filter_active(
        Grade.objects.filter(level__in=levels).select_related("level"),
        include_inactive=include_inactive,
    )


def grade_or_404(institution, public_id):
    return _get(
        Grade.objects.filter(level__institution=institution).select_related("level"),
        public_id,
        "Grade",
    )


def grade_for_payload(institution, public_id):
    return _get_payload(Grade.objects.filter(level__institution=institution), public_id, "el grado")


def subjects(institution, *, include_inactive=False):
    return _filter_active(
        Subject.objects.filter(institution=institution).prefetch_related("levels"),
        include_inactive=include_inactive,
    )


def subject_or_404(institution, public_id):
    return _get(
        Subject.objects.filter(institution=institution).prefetch_related("levels"),
        public_id,
        "Subject",
    )


def subject_for_payload(public_id):
    return _get_payload(Subject.objects.all(), public_id, "el curso")


def level_subjects(level):
    return LevelSubject.objects.filter(level=level).select_related("level", "subject")


_SECTION_RELATED = (
    "offering__grade__level",
    "offering__shift__campus",
    "offering__academic_cycle",
    "default_classroom",
)


def sections(institution, *, include_inactive=False, academic_cycle_id=None, grade_id=None):
    queryset = Section.objects.filter(
        offering__academic_cycle__institution=institution
    ).select_related(*_SECTION_RELATED)
    queryset = _filter_active(queryset, include_inactive=include_inactive)
    if academic_cycle_id:
        queryset = queryset.filter(offering__academic_cycle__public_id=academic_cycle_id)
    if grade_id:
        queryset = queryset.filter(offering__grade__public_id=grade_id)
    return queryset


def section_or_404(institution, public_id):
    return _get(
        Section.objects.filter(offering__academic_cycle__institution=institution).select_related(
            *_SECTION_RELATED
        ),
        public_id,
        "Section",
    )


def section_for_payload(public_id):
    return _get_payload(Section.objects.all(), public_id, "la sección")


_CLASS_SESSION_RELATED = (
    "section__offering__grade__level",
    "section__offering__shift__campus",
    "subject",
    "schedule_block",
    "classroom",
)


def _with_current_teacher(queryset):
    """
    S3: the current teacher of every session (RF-HOR-004) as annotations, so a
    page of sessions does not run ``ClassSession.current_teacher`` once per row.
    Same rule as that property: the section's current assignment for the subject.
    """
    current = TeachingAssignment.objects.filter(
        academic_cycle=OuterRef("academic_cycle"),
        section=OuterRef("section"),
        subject=OuterRef("subject"),
        ends_on__isnull=True,
    ).order_by("-starts_on")
    return queryset.annotate(
        _current_teacher_public_id=Subquery(
            current.values("teacher__teacher_profile__public_id")[:1]
        ),
        _current_teacher_first_name=Subquery(current.values("teacher__first_name")[:1]),
        _current_teacher_last_name=Subquery(current.values("teacher__last_name")[:1]),
    )


def class_sessions(section, *, include_inactive=False):
    queryset = _with_current_teacher(
        ClassSession.objects.filter(section=section).select_related(*_CLASS_SESSION_RELATED)
    )
    return _filter_active(queryset, include_inactive=include_inactive)


def class_session_or_404(institution, public_id):
    return _get(
        _with_current_teacher(
            ClassSession.objects.filter(
                section__offering__academic_cycle__institution=institution
            ).select_related(*_CLASS_SESSION_RELATED)
        ),
        public_id,
        "Class session",
    )


def weekly_load_report(section):
    """
    RF-HOR-007: for every subject in the section's grade study plan, compare
    the weekly hours declared for that (level, subject) pair against the
    periods actually scheduled for this section (active class sessions).

    The declared load lives on ``LevelSubject.weekly_hours`` (RF-EST-006),
    not on ``CurriculumPlan`` itself, which only says a subject belongs to
    the grade's plan for this cycle -- not how many periods a week. A
    subject in the plan but not linked at the level has no declared load to
    compare against, so ``declared_weekly_hours`` and ``matches`` come back
    ``None`` rather than treating it as a mismatch.
    """
    grade = section.grade
    plans = CurriculumPlan.objects.filter(
        academic_cycle=section.academic_cycle, grade=grade, is_active=True
    ).select_related("subject")
    weekly_hours_by_subject = dict(
        LevelSubject.objects.filter(
            level=grade.level, subject_id__in=[plan.subject_id for plan in plans]
        ).values_list("subject_id", "weekly_hours")
    )
    scheduled_by_subject = dict(
        ClassSession.objects.filter(section=section, is_active=True)
        .values("subject_id")
        .annotate(count=Count("id"))
        .values_list("subject_id", "count")
    )

    rows = []
    for plan in plans:
        declared = weekly_hours_by_subject.get(plan.subject_id)
        scheduled = scheduled_by_subject.get(plan.subject_id, 0)
        rows.append(
            {
                "subject": plan.subject,
                "declared_weekly_hours": declared,
                "scheduled_periods": scheduled,
                "matches": (declared == scheduled) if declared is not None else None,
            }
        )
    return rows


_CURRICULUM_PLAN_RELATED = ("academic_cycle", "grade__level", "subject")


def curriculum_plans(institution, *, include_inactive=False, academic_cycle_id=None, grade_id=None):
    queryset = CurriculumPlan.objects.filter(
        academic_cycle__institution=institution
    ).select_related(*_CURRICULUM_PLAN_RELATED)
    queryset = _filter_active(queryset, include_inactive=include_inactive)
    if academic_cycle_id:
        queryset = queryset.filter(academic_cycle__public_id=academic_cycle_id)
    if grade_id:
        queryset = queryset.filter(grade__public_id=grade_id)
    return queryset


def curriculum_plan_or_404(institution, public_id):
    return _get(
        CurriculumPlan.objects.filter(academic_cycle__institution=institution).select_related(
            *_CURRICULUM_PLAN_RELATED
        ),
        public_id,
        "Curriculum plan",
    )


# Everything ``TeachingAssignmentSerializer`` reads, so a page costs one query.
_TEACHING_ASSIGNMENT_RELATED = (
    "academic_cycle",
    "section__offering__grade",
    "subject",
    "teacher__teacher_profile",
)


def teaching_assignment_history(institution, *, teacher=None, academic_cycle=None):
    queryset = TeachingAssignment.objects.filter(
        academic_cycle__institution=institution
    ).select_related(*_TEACHING_ASSIGNMENT_RELATED)
    if teacher is not None:
        queryset = queryset.filter(teacher=teacher)
    if academic_cycle is not None:
        queryset = queryset.filter(academic_cycle=academic_cycle)
    return queryset.order_by("-academic_cycle__starts_on", "-starts_on", "-created_at")


def teaching_assignments(
    institution,
    *,
    academic_cycle=None,
    section=None,
    subject=None,
    teacher=None,
    current=None,
):
    """
    AD2/AD4: teaching assignments filtered on the server, in the order a
    timetable is read (grade, section, subject, then the most recent period).

    ``current=True`` keeps only the assignments in force (``ends_on`` null),
    ``current=False`` only the finished ones; ``None`` keeps both.
    """
    queryset = TeachingAssignment.objects.filter(
        academic_cycle__institution=institution
    ).select_related(*_TEACHING_ASSIGNMENT_RELATED)
    if academic_cycle is not None:
        queryset = queryset.filter(academic_cycle=academic_cycle)
    if section is not None:
        queryset = queryset.filter(section=section)
    if subject is not None:
        queryset = queryset.filter(subject=subject)
    if teacher is not None:
        queryset = queryset.filter(teacher=teacher)
    if current is not None:
        queryset = queryset.filter(ends_on__isnull=current)
    return queryset.order_by(
        "-academic_cycle__starts_on",
        "section__offering__grade__level__sequence",
        "section__offering__grade__sequence",
        "section__name",
        "subject__name",
        "-starts_on",
        "pk",
    )


def assignment_matrix_sections(academic_cycle, *, grade=None):
    """AD3: active sections of the cycle, one matrix row each, in pedagogical order."""
    queryset = Section.objects.filter(
        offering__academic_cycle=academic_cycle, is_active=True
    ).select_related("offering__grade__level", "offering__shift")
    if grade is not None:
        queryset = queryset.filter(offering__grade=grade)
    return queryset.order_by(
        "offering__grade__level__sequence",
        "offering__grade__sequence",
        "offering__shift__name",
        "name",
        "pk",
    )


def assignment_matrix_rows(academic_cycle, sections):
    """
    AD3: section x subject cells for ``sections`` (usually one page of
    ``assignment_matrix_sections``). The columns of a row are the subjects of
    the cycle's curriculum plan for that section's grade; a cell carries the
    current assignment or ``None`` — exactly what activation demands
    (``academic_cycle_opening_gaps``). Three queries whatever the page size.
    """
    sections = list(sections)
    grade_ids = {section.offering.grade_id for section in sections}
    subjects_by_grade = {}
    for plan in (
        CurriculumPlan.objects.filter(
            academic_cycle=academic_cycle, grade_id__in=grade_ids, is_active=True
        )
        .select_related("subject")
        .order_by("subject__name", "pk")
    ):
        subjects_by_grade.setdefault(plan.grade_id, []).append(plan.subject)

    current = {
        (assignment.section_id, assignment.subject_id): assignment
        for assignment in TeachingAssignment.objects.filter(
            academic_cycle=academic_cycle, section__in=sections, ends_on__isnull=True
        ).select_related("teacher__teacher_profile")
    }
    return [
        {
            "section": section,
            "cells": [
                {"subject": subject, "assignment": current.get((section.id, subject.id))}
                for subject in subjects_by_grade.get(section.offering.grade_id, [])
            ],
        }
        for section in sections
    ]


def _section_match_key(section):
    """A section is the same across cycles by grade + shift + name, never by id."""
    return (section.offering.grade_id, section.offering.shift_id, section.name)


def teaching_assignment_clone_preview(*, source_cycle, target_cycle):
    """
    AD2: what cloning the current assignments of ``source_cycle`` into
    ``target_cycle`` would do, row by row, without writing anything.

    Sections are matched by grade, shift and name: cloning the structure gives
    every section a new identifier, but "Primero Básico A, matutina" still
    means the same group. Each row is ``pending`` (can be created),
    ``already_assigned`` (the target already has a current teacher for that
    section and subject) or ``unmatched`` (no equivalent active section).
    """
    target_sections = {
        _section_match_key(section): section
        for section in Section.objects.filter(
            offering__academic_cycle=target_cycle, is_active=True
        ).select_related("offering__grade", "offering__shift")
    }
    already_assigned = set(
        target_cycle.teaching_assignments.filter(ends_on__isnull=True).values_list(
            "section_id", "subject_id"
        )
    )
    rows = []
    for assignment in (
        source_cycle.teaching_assignments.filter(ends_on__isnull=True)
        .select_related(
            "section__offering__grade__level",
            "section__offering__shift",
            "subject",
            "teacher__teacher_profile",
        )
        .order_by(
            "section__offering__grade__level__sequence",
            "section__offering__grade__sequence",
            "section__name",
            "subject__name",
            "pk",
        )
    ):
        target_section = target_sections.get(_section_match_key(assignment.section))
        if target_section is None:
            status = "unmatched"
        elif (target_section.id, assignment.subject_id) in already_assigned:
            status = "already_assigned"
        else:
            status = "pending"
        rows.append(
            {
                "source_assignment": assignment,
                "section": assignment.section,
                "subject": assignment.subject,
                "teacher": assignment.teacher,
                "target_section": target_section,
                "status": status,
            }
        )
    summary = {"total": len(rows), "pending": 0, "already_assigned": 0, "unmatched": 0}
    for row in rows:
        summary[row["status"]] += 1
    return {
        "source_cycle": source_cycle,
        "target_cycle": target_cycle,
        "suggested_starts_on": target_cycle.starts_on,
        "summary": summary,
        "rows": rows,
    }


def teaching_assignment_or_404(public_id):
    return _get(
        TeachingAssignment.objects.select_related("academic_cycle").all(),
        public_id,
        "Teaching assignment",
    )


def historical_cycle_or_404(institution, public_id):
    queryset = (
        AcademicCycle.objects.filter(institution=institution)
        .prefetch_related(
            Prefetch(
                "grade_offerings",
                queryset=(
                    GradeOffering.objects.select_related("grade__level", "shift__campus")
                    .prefetch_related(
                        Prefetch("sections", queryset=Section.objects.order_by("name"))
                    )
                    .order_by("grade__level__sequence", "grade__sequence", "shift__name")
                ),
            ),
            Prefetch(
                "curriculum_plans",
                queryset=CurriculumPlan.objects.select_related("grade__level", "subject").order_by(
                    "grade__level__sequence", "grade__sequence", "subject__name"
                ),
            ),
            Prefetch(
                "teaching_assignments",
                queryset=TeachingAssignment.objects.select_related(
                    *_TEACHING_ASSIGNMENT_RELATED
                ).order_by("starts_on", "created_at"),
            ),
        )
        .annotate(
            _enrolment_total=Count("enrolments", distinct=True),
            _enrolment_active=Count(
                "enrolments", filter=Q(enrolments__status="active"), distinct=True
            ),
            _enrolment_withdrawn=Count(
                "enrolments", filter=Q(enrolments__status="withdrawn"), distinct=True
            ),
            _enrolment_completed=Count(
                "enrolments", filter=Q(enrolments__status="completed"), distinct=True
            ),
            _enrolment_cancelled=Count(
                "enrolments", filter=Q(enrolments__status="cancelled"), distinct=True
            ),
        )
    )
    return _get(queryset, public_id, "el ciclo escolar")


def _get(queryset, public_id, label):
    try:
        return queryset.get(public_id=public_id)
    except queryset.model.DoesNotExist as exc:
        raise ResourceNotFoundError(f"No se encontró {label}.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError(f"No se encontró {label}.") from exc


def _get_payload(queryset, public_id, label):
    try:
        return queryset.get(public_id=public_id)
    except (queryset.model.DoesNotExist, ValueError, TypeError) as exc:
        raise DomainError(f"No se encontró {label}.") from exc


def frozen_subject_result_history(*, enrolment, subject):
    """Every frozen row for this subarea, most recent first (RF-RES-007/009)."""
    return FrozenSubjectResult.objects.filter(enrolment=enrolment, subject=subject)


def latest_frozen_subject_result(*, enrolment, subject):
    """The current, authoritative frozen value for this subarea, or ``None``
    if the cycle was never frozen for this enrolment/subject."""
    return frozen_subject_result_history(enrolment=enrolment, subject=subject).first()


def frozen_subject_results_for_enrolment(*, enrolment):
    """Every frozen subarea row for this enrolment (any cycle), most recent
    version of each subarea first -- used to build a boleta (RF-RES-008)."""
    return FrozenSubjectResult.objects.filter(enrolment=enrolment).select_related("subject")


def frozen_promotion_result_history(*, enrolment):
    """Every frozen promotion row for this enrolment, most recent first."""
    return FrozenPromotionResult.objects.filter(enrolment=enrolment)


def latest_frozen_promotion_result(*, enrolment):
    """The current, authoritative frozen promotion outcome, or ``None`` if
    the cycle was never frozen for this enrolment."""
    return frozen_promotion_result_history(enrolment=enrolment).first()


def next_active_grade(*, grade):
    """Return the next configured grade in the institution's pedagogical order."""
    return (
        Grade.objects.filter(institution_id=grade.institution_id, is_active=True)
        .filter(
            Q(level__sequence__gt=grade.level.sequence)
            | Q(level_id=grade.level_id, sequence__gt=grade.sequence)
        )
        .select_related("level")
        .order_by("level__sequence", "sequence", "name", "pk")
        .first()
    )


def class_schedule_publication(academic_cycle):
    """
    Existing publication row, or an unsaved default (never published).

    Read-only: does not create a row, so checking status has no side effect.
    """
    return ClassSchedulePublication.objects.filter(
        academic_cycle=academic_cycle
    ).first() or ClassSchedulePublication(academic_cycle=academic_cycle)


# --------------------------------------------------------------------------- #
# current teaching assignment
# --------------------------------------------------------------------------- #


def current_teaching_assignment(*, academic_cycle, section, subject):
    """
    The current (``ends_on`` is null) assignment for a section and subject, or
    ``None`` when nobody teaches it yet. The exclusion constraint guarantees at
    most one current row per (cycle, section, subject).
    """
    return (
        TeachingAssignment.objects.filter(
            academic_cycle=academic_cycle,
            section=section,
            subject=subject,
            ends_on__isnull=True,
        )
        .select_related("teacher")
        .first()
    )


# --------------------------------------------------------------------------- #
# cycle readiness: activation, closure and revert-to-draft (C7, D1, D3, D6)
# --------------------------------------------------------------------------- #


def _gap(code, message, *, grade=None, section=None, subject=None):
    return {
        "code": code,
        "message": message,
        "grade": grade,
        "section": section,
        "subject": subject,
    }


def academic_cycle_opening_gaps(cycle):
    """
    What still blocks activating ``cycle`` (RF-CIC-003, RF-EST-010).

    Each gap is ``{code, message, grade, section, subject}`` so the activation
    checklist can link every item to the screen that solves it. The messages
    are full sentences; ``activate_academic_cycle`` joins them into its error.
    """
    offerings = list(
        cycle.grade_offerings.filter(is_active=True)
        .select_related("grade", "shift")
        .prefetch_related("sections")
        .order_by("grade__level__sequence", "grade__sequence", "shift__name", "pk")
    )
    if not offerings:
        return [_gap("no_grade_offerings", "Falta al menos una oferta de grado.")]

    gaps = []
    subjects_by_grade = {}
    for plan in (
        cycle.curriculum_plans.filter(is_active=True)
        .select_related("subject")
        .order_by("subject__name", "pk")
    ):
        subjects_by_grade.setdefault(plan.grade_id, []).append(plan.subject)

    # Current (ends_on is null) teaching assignments, keyed by the pair every
    # subarea of a section must clear (RF-EST-010): no partial credit for a
    # closed, superseded assignment.
    assigned_pairs = set(
        cycle.teaching_assignments.filter(ends_on__isnull=True).values_list(
            "section_id", "subject_id"
        )
    )

    reported_plan_gaps = set()
    for offering in offerings:
        grade = offering.grade
        active_sections = [section for section in offering.sections.all() if section.is_active]
        if not active_sections:
            gaps.append(
                _gap(
                    "missing_sections",
                    f"Faltan secciones del grado '{grade.name}' en la jornada "
                    f"'{offering.shift.name}'.",
                    grade=grade,
                )
            )
        subjects = subjects_by_grade.get(offering.grade_id)
        if subjects is None:
            if offering.grade_id not in reported_plan_gaps:
                gaps.append(
                    _gap(
                        "missing_curriculum_plan",
                        f"Falta el plan de estudios del grado '{grade.name}'.",
                        grade=grade,
                    )
                )
                reported_plan_gaps.add(offering.grade_id)
            continue
        for section in active_sections:
            for subject in subjects:
                if (section.id, subject.id) not in assigned_pairs:
                    gaps.append(
                        _gap(
                            "missing_teacher",
                            f"Falta asignar docente para '{subject.name}' en la sección "
                            f"'{section.name}' del grado '{grade.name}'.",
                            grade=grade,
                            section=section,
                            subject=subject,
                        )
                    )
    return gaps


def academic_cycle_closure_gaps(cycle):
    """
    Evaluation units that block closing the cycle (RF-CIC-004): still open, or
    closed with a recovery window that has not expired yet.

    Read through the reverse relation only (``cycle.evaluation_units``), the
    same way ``Section.active_enrolment_count`` reads ``enrolments`` without
    importing that domain's models — ``evaluation`` depends on ``academics``,
    not the other way around (domain-map.md).
    """
    today = timezone.localdate()
    gaps = []
    for unit in cycle.evaluation_units.order_by("number"):
        if unit.status != "closed":
            gaps.append(
                {
                    "code": "evaluation_unit_open",
                    "message": f"La unidad de evaluación '{unit.name}' sigue abierta.",
                }
            )
        elif unit.recovery_ends_on is not None and today <= unit.recovery_ends_on:
            gaps.append(
                {
                    "code": "recovery_window_open",
                    "message": (
                        f"La ventana de recuperación de la unidad '{unit.name}' aún no vence."
                    ),
                }
            )
    return gaps


def _plural(count, singular, plural):
    return singular if count == 1 else plural


def academic_cycle_revert_blockers(cycle):
    """
    Activity that forbids sending ``cycle`` back to draft (D3, D6, RF-CIC-008).

    D6 lists five kinds of activity: enrolments, grades, attendance movements,
    closed evaluation units and issued documents. ``academics`` sits below all
    of those domains (domain-map.md), so none of their modules is imported
    here: every count walks a reverse relation by name, the mechanism
    ``academic_cycle_closure_gaps`` already uses for ``evaluation_units``.

    Attendance events carry no cycle: like
    ``attendance.services.resolve_academic_cycle_for``, an event belongs to the
    cycle of its shift's institution whose dates cover ``event_date``. Cycles of
    one institution never overlap (``academic_cycle_no_overlapping_dates``), so
    that mapping is exact.

    Returns ``[{code, count, message}]``, empty when the cycle has no activity.
    """
    enrolments = cycle.enrolments.all()
    counts = [
        (
            "enrolments",
            enrolments.count(),
            ("matrícula", "matrículas"),
        ),
        (
            "grades",
            (enrolments.aggregate(total=Count("grades"))["total"] or 0)
            + (enrolments.aggregate(total=Count("recovery_grades"))["total"] or 0),
            ("nota registrada", "notas registradas"),
        ),
        (
            "attendance_events",
            Shift.objects.filter(campus__institution_id=cycle.institution_id).aggregate(
                total=Count(
                    "attendance_events",
                    filter=Q(
                        attendance_events__event_date__gte=cycle.starts_on,
                        attendance_events__event_date__lte=cycle.ends_on,
                    ),
                )
            )["total"]
            or 0,
            ("movimiento de asistencia", "movimientos de asistencia"),
        ),
        (
            "closed_evaluation_units",
            cycle.evaluation_units.filter(status="closed").count(),
            ("unidad de evaluación cerrada", "unidades de evaluación cerradas"),
        ),
        (
            "issued_documents",
            enrolments.aggregate(total=Count("document_issuances"))["total"] or 0,
            ("documento emitido", "documentos emitidos"),
        ),
    ]
    return [
        {"code": code, "count": count, "message": f"Tiene {count} {_plural(count, *nouns)}."}
        for code, count, nouns in counts
        if count
    ]


def other_active_cycle(cycle):
    """The institution's ACTIVE cycle when it is not ``cycle`` itself (D1)."""
    return (
        AcademicCycle.objects.filter(
            institution_id=cycle.institution_id, status=AcademicCycle.CycleStatus.ACTIVE
        )
        .exclude(pk=cycle.pk)
        .first()
    )


def academic_cycle_readiness(cycle):
    """
    Everything the cycle screen needs to explain its enabled and disabled
    actions without trying them first (C7, D1, D6): activation checklist,
    revert-to-draft blockers, closure gaps and the other active cycle.
    """
    status = AcademicCycle.CycleStatus
    active_cycle = other_active_cycle(cycle)

    if cycle.status == status.DRAFT:
        activation_gaps = []
        if active_cycle is not None:
            activation_gaps.append(
                _gap(
                    "active_cycle_exists",
                    f"Hay que cerrar el ciclo activo '{active_cycle.name}' antes de activar otro.",
                )
            )
        activation_gaps.extend(academic_cycle_opening_gaps(cycle))
    else:
        activation_gaps = [
            _gap("invalid_status", "Solo se puede activar un ciclo escolar en preparación.")
        ]

    if cycle.status == status.ACTIVE:
        revert_blockers = academic_cycle_revert_blockers(cycle)
        close_gaps = academic_cycle_closure_gaps(cycle)
    else:
        revert_blockers = [
            {
                "code": "invalid_status",
                "count": None,
                "message": "Solo se puede volver a borrador un ciclo escolar activo.",
            }
        ]
        close_gaps = [
            {
                "code": "invalid_status",
                "message": "Solo se puede cerrar un ciclo escolar activo.",
            }
        ]

    return {
        "activation": {"ready": not activation_gaps, "gaps": activation_gaps},
        "revert": {"allowed": not revert_blockers, "blockers": revert_blockers},
        "close": {"ready": not close_gaps, "gaps": close_gaps},
        "active_cycle": active_cycle,
    }


def non_computable_days(academic_cycle):
    """Active non-computable days of the cycle, by date (RF-JOR-010)."""
    return academic_cycle.non_computable_days.filter(is_active=True).order_by("day")


def non_computable_day_or_404(institution, public_id):
    return _get(
        NonComputableDay.objects.filter(
            academic_cycle__institution=institution, is_active=True
        ).select_related("academic_cycle"),
        public_id,
        "el día no computable",
    )
