"""
Read-side query helpers for the academic catalogue.

Every list and detail payload is built from the querysets defined here, so the
annotations the serializers depend on always exist and no view triggers a
hidden per-row count.
"""

from django.db.models import Count, Q
from rest_framework.exceptions import NotFound

from apps.academics.models import Campus, Grade, Institution, Level, LevelSubject, Shift, Subject


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


def _get(queryset, public_id, label):
    try:
        return queryset.get(public_id=public_id)
    except queryset.model.DoesNotExist as exc:
        raise NotFound(f"{label} not found.") from exc
    except (ValueError, TypeError) as exc:  # malformed public_id
        raise NotFound(f"{label} not found.") from exc
