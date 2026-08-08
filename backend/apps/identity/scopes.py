from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone

from apps.identity.models import ScopeGrant
from apps.students.models import Student


def active_scope_grants(*, user, codename, when=None):
    when = when or timezone.now()
    return (
        ScopeGrant.objects.filter(
            is_active=True,
            assignment__user=user,
            assignment__is_active=True,
            assignment__starts_at__lte=when,
            assignment__role__permissions__codename=codename,
            starts_at__lte=when,
        )
        .filter(
            Q(assignment__ends_at__isnull=True) | Q(assignment__ends_at__gte=when),
            Q(ends_at__isnull=True) | Q(ends_at__gte=when),
        )
        .select_related(
            "institution",
            "academic_cycle",
            "grade",
            "section",
            "subject",
            "teaching_assignment__section",
            "student",
        )
        .distinct()
    )


def has_effective_scope_grant(*, user, codename, when=None):
    return any(
        grant.has_effective_scope()
        for grant in active_scope_grants(user=user, codename=codename, when=when)
    )


def student_queryset(*, user, codename, queryset=None, when=None):
    """Return only students covered by the user's effective grants."""
    queryset = queryset if queryset is not None else Student.objects.all()
    grants = active_scope_grants(user=user, codename=codename, when=when)
    allowed = Q(pk__in=[])

    for grant in grants:
        student_filter = _student_filter_for_grant(grant)
        if student_filter is not None:
            allowed |= student_filter

    return queryset.filter(allowed).distinct()


def authorized_student_queryset(*, user, codename, queryset=None, when=None):
    """Resolve a student queryset or deny when permission or scope is missing."""
    if not user.has_atomic_permission(codename, when=when):
        raise PermissionDenied("Actor lacks the required permission.")
    if not has_effective_scope_grant(user=user, codename=codename, when=when):
        raise PermissionDenied("Actor lacks an effective scope grant.")
    return student_queryset(user=user, codename=codename, queryset=queryset, when=when)


def can_access_student(*, user, codename, student, when=None):
    try:
        return (
            authorized_student_queryset(user=user, codename=codename, when=when)
            .filter(pk=student.pk)
            .exists()
        )
    except PermissionDenied:
        return False


def scope_matches(*, user, codename, scope, when=None):
    if not scope:
        return False
    return any(
        grant_matches_scope(grant, scope, when=when)
        for grant in active_scope_grants(user=user, codename=codename, when=when)
    )


def grant_matches_scope(grant, scope, *, when=None):
    """Evaluate one effective grant against a contextual resource scope."""
    when = when or timezone.now()
    if not grant.is_active_at(when) or not grant.has_effective_scope() or not scope:
        return False

    student = scope.get("student")
    if student is not None:
        student_id = getattr(student, "pk", student)
        return (
            Student.objects.filter(pk=student_id)
            .filter(_student_filter_for_grant(grant) or Q(pk__in=[]))
            .exists()
        )

    context = _scope_context(scope)
    for field_name in ScopeGrant.SCOPE_FIELDS:
        grant_value = getattr(grant, field_name)
        if grant_value in (None, ""):
            continue
        context_value = context.get(field_name)
        if context_value is None or _primary_key(context_value) != _primary_key(grant_value):
            return False
    return True


def _student_filter_for_grant(grant):
    if not grant.has_effective_scope() or grant.subject_id or grant.module_key:
        return None

    conditions = Q()
    has_student_dimension = False
    has_enrolment_dimension = False

    if grant.student_id:
        conditions &= Q(pk=grant.student_id)
        has_student_dimension = True
    if grant.institution_id:
        conditions &= Q(
            enrolments__section__offering__academic_cycle__institution_id=grant.institution_id
        )
        has_enrolment_dimension = True
    if grant.academic_cycle_id:
        conditions &= Q(enrolments__academic_cycle_id=grant.academic_cycle_id)
        has_enrolment_dimension = True
    if grant.grade_id:
        conditions &= Q(enrolments__grade_id=grant.grade_id)
        has_enrolment_dimension = True
    if grant.section_id:
        conditions &= Q(enrolments__section_id=grant.section_id)
        has_enrolment_dimension = True
    if grant.teaching_assignment_id:
        conditions &= Q(enrolments__section_id=grant.teaching_assignment.section_id)
        has_enrolment_dimension = True

    if has_enrolment_dimension:
        conditions &= Q(enrolments__is_active=True, enrolments__status="active")
    if not has_student_dimension and not has_enrolment_dimension:
        return None
    return conditions


def _scope_context(scope):
    context = dict(scope)
    section = context.get("section")
    teaching_assignment = context.get("teaching_assignment")

    if teaching_assignment is not None:
        section = teaching_assignment.section
        context.setdefault("section", section)
        context.setdefault("academic_cycle", teaching_assignment.academic_cycle)
        context.setdefault("subject", teaching_assignment.subject)
    if section is not None:
        context.setdefault("institution", section.academic_cycle.institution)
        context.setdefault("academic_cycle", section.academic_cycle)
        context.setdefault("grade", section.grade)
    return context


def _primary_key(value):
    return getattr(value, "pk", value)
