"""
Read-side query helpers for the academic catalogue.

Every list and detail payload is built from the querysets defined here, so the
annotations the serializers depend on always exist and no view triggers a
hidden per-row count.
"""

from django.db.models import Count, Q
from rest_framework.exceptions import NotFound

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


def resolve_institution(request):
    """
    Resolve the institution the request operates on.

    Until institutional scoping lands (RF-EST / identity-access), the API works
    against the single configured institution. Centralising it here keeps the
    change to one place.
    """
    institution = Institution.objects.order_by("pk").first()
    if institution is None:
        raise NotFound("No institution is configured yet.")
    return institution


def _wants_inactive(request):
    return str(request.query_params.get("include_inactive", "")).lower() in {
        "1",
        "true",
        "yes",
    }


def _filter_active(queryset, request):
    if _wants_inactive(request):
        return queryset
    return queryset.filter(is_active=True)


def campuses_all(institution):
    # annotate() clears the model's default ordering, so list order is explicit.
    return (
        Campus.objects.filter(institution=institution)
        .annotate(_shift_count=Count("shifts", filter=Q(shifts__is_active=True), distinct=True))
        .order_by("name")
    )


def campuses(institution, request):
    return _filter_active(campuses_all(institution), request)


def campus_or_404(institution, public_id):
    return _get(campuses_all(institution), public_id, "Campus")


def shifts(campus, request):
    return _filter_active(Shift.objects.filter(campus=campus).select_related("campus"), request)


def shift_or_404(institution, public_id):
    return _get(
        Shift.objects.filter(campus__institution=institution).select_related("campus"),
        public_id,
        "Shift",
    )


def levels(institution, request):
    return _filter_active(levels_all(institution), request)


def levels_all(institution):
    return (
        Level.objects.filter(institution=institution)
        .annotate(
            _grade_count=Count("grades", filter=Q(grades__is_active=True), distinct=True),
            _subject_count=Count("level_subjects", distinct=True),
        )
        .order_by("sequence", "name")
    )


def level_or_404(institution, public_id):
    return _get(levels_all(institution), public_id, "Level")


def grades(level, request):
    return _filter_active(Grade.objects.filter(level=level).select_related("level"), request)


def grade_or_404(institution, public_id):
    return _get(
        Grade.objects.filter(level__institution=institution).select_related("level"),
        public_id,
        "Grade",
    )


def subjects(institution, request):
    return _filter_active(
        Subject.objects.filter(institution=institution).prefetch_related("levels"), request
    )


def subject_or_404(institution, public_id):
    return _get(
        Subject.objects.filter(institution=institution).prefetch_related("levels"),
        public_id,
        "Subject",
    )


def level_subjects(level):
    return LevelSubject.objects.filter(level=level).select_related("level", "subject")


# --------------------------------------------------------------------------- #
# cycle-scoped structure
# --------------------------------------------------------------------------- #


def cycles_all(institution):
    return (
        AcademicCycle.objects.filter(institution=institution)
        .annotate(
            _offering_count=Count(
                "grade_offerings", filter=Q(grade_offerings__is_active=True), distinct=True
            )
        )
        .order_by("-starts_on", "name")
    )


def cycles(institution, request):
    return _filter_active(cycles_all(institution), request)


def cycle_or_404(institution, public_id):
    return _get(cycles_all(institution), public_id, "Academic cycle")


def offerings_all(institution):
    """
    Offerings carry the counts the list needs: how many sections they hold and
    how many students those sections already take (RF-EST-008).
    """
    return (
        GradeOffering.objects.filter(academic_cycle__institution=institution)
        .select_related("academic_cycle", "grade", "grade__level", "shift", "shift__campus")
        .annotate(
            _section_count=Count("sections", filter=Q(sections__is_active=True), distinct=True),
            _enrolment_count=Count(
                "sections__enrolments",
                filter=Q(sections__enrolments__status="active"),
                distinct=True,
            ),
        )
        .order_by("shift__campus__name", "grade__level__sequence", "grade__sequence")
    )


def cycle_offerings(cycle, request):
    return _filter_active(offerings_all(cycle.institution).filter(academic_cycle=cycle), request)


def offering_or_404(institution, public_id):
    return _get(offerings_all(institution), public_id, "Grade offering")


def sections_all(institution):
    return (
        Section.objects.filter(offering__academic_cycle__institution=institution)
        .select_related(
            "offering",
            "offering__academic_cycle",
            "offering__grade",
            "offering__shift",
            "offering__shift__campus",
        )
        .annotate(
            _active_enrolments=Count(
                "enrolments", filter=Q(enrolments__status="active"), distinct=True
            ),
            _assignment_count=Count(
                "teaching_assignments",
                filter=Q(teaching_assignments__ends_on__isnull=True),
                distinct=True,
            ),
        )
        .order_by("name")
    )


def offering_sections(offering, request):
    return _filter_active(sections_all(offering.institution).filter(offering=offering), request)


def section_or_404(institution, public_id):
    return _get(sections_all(institution), public_id, "Section")


def curriculum_entries(cycle, grade=None):
    """Plan of a cycle, narrowed to one grade when the caller asks for it."""
    queryset = CurriculumPlan.objects.filter(academic_cycle=cycle).select_related(
        "academic_cycle", "grade", "grade__level", "subject"
    )
    if grade is not None:
        queryset = queryset.filter(grade=grade)
    return queryset


def curriculum_entry_or_404(institution, public_id):
    return _get(
        CurriculumPlan.objects.filter(academic_cycle__institution=institution).select_related(
            "academic_cycle", "grade", "grade__level", "subject"
        ),
        public_id,
        "Curriculum entry",
    )


def assignments_all(institution):
    return TeachingAssignment.objects.filter(
        academic_cycle__institution=institution
    ).select_related("academic_cycle", "section", "section__offering", "subject", "teacher")


def section_assignments(section, request):
    """
    Open assignments only, unless the caller asks for the closed ones too. The
    flag is the same ``include_inactive`` used everywhere else, because for an
    assignment "no longer in force" is what being inactive means.
    """
    queryset = assignments_all(section.academic_cycle.institution).filter(section=section)
    if _wants_inactive(request):
        return queryset
    return queryset.filter(ends_on__isnull=True)


def assignment_or_404(institution, public_id):
    return _get(assignments_all(institution), public_id, "Teaching assignment")


def _get(queryset, public_id, label):
    try:
        return queryset.get(public_id=public_id)
    except queryset.model.DoesNotExist as exc:
        raise NotFound(f"{label} not found.") from exc
    except (ValueError, TypeError) as exc:  # malformed public_id
        raise NotFound(f"{label} not found.") from exc
