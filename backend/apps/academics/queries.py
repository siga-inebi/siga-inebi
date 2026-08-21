"""Read-side queries for the academic-structure domain."""

from django.db.models import Count, Prefetch, Q

from apps.academics.models import (
    AcademicCycle,
    Campus,
    CurriculumPlan,
    Grade,
    GradeOffering,
    Institution,
    Level,
    LevelSubject,
    Section,
    Shift,
    Subject,
    TeachingAssignment,
)
from apps.common.exceptions import DomainError, ResourceNotFoundError


def resolve_institution():
    institution = Institution.objects.order_by("pk").first()
    if institution is None:
        raise ResourceNotFoundError("No institution is configured yet.")
    return institution


def academic_cycles(institution):
    return AcademicCycle.objects.filter(institution=institution).order_by("-year", "starts_on")


def academic_cycle_or_404(institution, public_id):
    return _get(academic_cycles(institution), public_id, "Academic cycle")


def academic_cycle_for_payload(public_id):
    return _get_payload(AcademicCycle.objects.all(), public_id, "Academic cycle")


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
    return _get(campuses_all(institution), public_id, "Campus")


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
    return _get_payload(Shift.objects.filter(campus__institution=institution), public_id, "Shift")


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
    return _get(levels_all(institution), public_id, "Level")


def grades(level, *, include_inactive=False):
    return _filter_active(
        Grade.objects.filter(level=level).select_related("level"), include_inactive=include_inactive
    )


def grade_or_404(institution, public_id):
    return _get(
        Grade.objects.filter(level__institution=institution).select_related("level"),
        public_id,
        "Grade",
    )


def grade_for_payload(institution, public_id):
    return _get_payload(Grade.objects.filter(level__institution=institution), public_id, "Grade")


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
    return _get_payload(Subject.objects.all(), public_id, "Subject")


def level_subjects(level):
    return LevelSubject.objects.filter(level=level).select_related("level", "subject")


_SECTION_RELATED = ("offering__grade__level", "offering__shift__campus", "offering__academic_cycle")


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
    return _get_payload(Section.objects.all(), public_id, "Section")


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


def teaching_assignment_history(institution, *, teacher=None, academic_cycle=None):
    queryset = TeachingAssignment.objects.filter(
        academic_cycle__institution=institution
    ).select_related("academic_cycle", "section", "subject", "teacher__teacher_profile")
    if teacher is not None:
        queryset = queryset.filter(teacher=teacher)
    if academic_cycle is not None:
        queryset = queryset.filter(academic_cycle=academic_cycle)
    return queryset.order_by("-academic_cycle__starts_on", "-starts_on", "-created_at")


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
                    "section", "subject", "teacher__teacher_profile"
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
    return _get(queryset, public_id, "Academic cycle")


def _get(queryset, public_id, label):
    try:
        return queryset.get(public_id=public_id)
    except queryset.model.DoesNotExist as exc:
        raise ResourceNotFoundError(f"{label} not found.") from exc
    except (ValueError, TypeError) as exc:
        raise ResourceNotFoundError(f"{label} not found.") from exc


def _get_payload(queryset, public_id, label):
    try:
        return queryset.get(public_id=public_id)
    except (queryset.model.DoesNotExist, ValueError, TypeError) as exc:
        raise DomainError(f"{label} not found.") from exc
