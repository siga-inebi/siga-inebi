from django.db.models import Q
from django.utils import timezone

from apps.academics.models import AcademicCycle, ClassSession, TeachingAssignment
from apps.audit.services import record_event
from apps.common.exceptions import AuthorizationError
from apps.identity.models import ScopeGrant
from apps.students.models import Student

WRITE_PERMISSION_CODENAMES = {
    "grade_write",
    "grade_correct",
    "attendance_record_entry",
    "attendance_record_exit",
    "attendance_record_manual",
    "attendance_declared_close",
    "attendance_scan",
    "attendance_credential_issue",
    "attendance_justification_resolve",
    "enrollment_create",
    "enrollment_update",
    "student_edit_basic",
    "document_upload",
    "document_issue",
}


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


def guardian_student_queryset(*, user, queryset=None):
    """Resolve the current, non-historical student scope derived from a guardian link."""
    queryset = queryset if queryset is not None else Student.objects.all()
    person = getattr(user, "person", None)
    guardian = getattr(person, "guardian_profile", None)
    if guardian is None or not guardian.is_active:
        return queryset.none()

    return queryset.filter(
        guardian_relations__guardian=guardian,
        guardian_relations__is_active=True,
        guardian_relations__starts_at__lte=timezone.localdate(),
        guardian_relations__ends_at__isnull=True,
    ).distinct()


def teacher_student_queryset(*, user, queryset=None, when=None):
    """Resolve current students in sections assigned to the account's teacher."""
    queryset = queryset if queryset is not None else Student.objects.all()
    assigned_sections = teaching_assignment_queryset(user=user, when=when)

    return queryset.filter(
        enrolments__section_id__in=assigned_sections.values("section_id"),
        enrolments__is_active=True,
        enrolments__status="active",
    ).distinct()


def effective_student_queryset(*, user, codename, queryset=None, when=None):
    """Return the additive student scope from grants, guardian links, and teaching assignments."""
    queryset = queryset if queryset is not None else Student.objects.all()
    granted_students = student_queryset(user=user, codename=codename, when=when)
    guardian_students = guardian_student_queryset(user=user)
    teacher_students = teacher_student_queryset(user=user, when=when)
    return queryset.filter(
        Q(pk__in=granted_students.values("pk"))
        | Q(pk__in=guardian_students.values("pk"))
        | Q(pk__in=teacher_students.values("pk"))
    ).distinct()


def authorized_student_queryset(*, user, codename, queryset=None, when=None):
    """Resolve a student queryset or deny when permission or scope is missing."""
    if not user.has_atomic_permission(codename, when=when):
        _audit_student_access_denied(user=user, codename=codename, reason="missing_permission")
        raise AuthorizationError("El actor no tiene el permiso requerido.")
    guardian_students = guardian_student_queryset(user=user)
    teacher_students = teacher_student_queryset(user=user, when=when)
    has_administrative_scope = has_effective_scope_grant(user=user, codename=codename, when=when)
    has_derived_scope = guardian_students.exists() or teacher_students.exists()
    if not has_administrative_scope and not has_derived_scope:
        _audit_student_access_denied(user=user, codename=codename, reason="missing_scope")
        raise AuthorizationError("El actor no tiene un alcance vigente asignado.")
    return effective_student_queryset(user=user, codename=codename, queryset=queryset, when=when)


def _audit_student_access_denied(*, user, codename, reason):
    """
    RF-BIT-004: this is the single choke point every student-scoped view goes
    through (directly or via ``can_access_student``), so auditing here covers
    the "encargado sin asociacion" scenario without duplicating the call at
    every view that resolves a student.
    """
    record_event(
        actor=user,
        action="identity.authorization.denied",
        resource="Student",
        context={"result": "denied", "reason": reason, "permission": codename},
    )


def can_access_student(*, user, codename, student, when=None):
    try:
        return (
            authorized_student_queryset(user=user, codename=codename, when=when)
            .filter(pk=student.pk)
            .exists()
        )
    except AuthorizationError:
        return False


def own_class_session_queryset(*, user, when=None):
    """
    Sessions a teacher account currently teaches (RF-HOR-010), derived from
    the exact (academic_cycle, section, subject) of their current teaching
    assignments -- not a looser per-section or per-subject match, which
    would leak sessions from an unrelated subject the same teacher happens
    to also teach elsewhere.
    """
    assignments = teaching_assignment_queryset(user=user, when=when)
    condition = Q(pk__in=[])
    for assignment in assignments:
        condition |= Q(
            academic_cycle_id=assignment.academic_cycle_id,
            section_id=assignment.section_id,
            subject_id=assignment.subject_id,
        )
    return ClassSession.objects.filter(condition)


def ward_class_session_queryset(*, user):
    """Sessions of the sections a guardian account's wards are actively enrolled in."""
    students = guardian_student_queryset(user=user)
    return ClassSession.objects.filter(
        section__enrolments__student__in=students,
        section__enrolments__is_active=True,
        section__enrolments__status="active",
    )


def has_own_schedule_scope(*, user):
    """True when the account is a teacher, or has at least one active ward."""
    person = getattr(user, "person", None)
    if person is None:
        return False
    if getattr(person, "teacher_profile", None) is not None:
        return True
    guardian = getattr(person, "guardian_profile", None)
    return guardian is not None and guardian.is_active


def my_weekly_schedule_queryset(*, user, when=None):
    """
    RF-HOR-010: the caller's own weekly schedule -- sessions they teach,
    union sessions of their wards' sections. Restricted to published
    schedules (RF-HOR-009): a draft schedule is not yet "sus asignaciones o
    tutela" in the sense the requirement means.
    """
    own = own_class_session_queryset(user=user, when=when)
    ward = ward_class_session_queryset(user=user)
    related = (
        "section__offering__grade",
        "section__offering__shift",
        "subject",
        "schedule_block",
    )
    return (
        ClassSession.objects.filter(Q(pk__in=own.values("pk")) | Q(pk__in=ward.values("pk")))
        .filter(
            is_active=True,
            academic_cycle__schedule_publication__published_at__isnull=False,
        )
        .select_related(*related)
        .distinct()
    )


def scope_matches(*, user, codename, scope, when=None):
    """Resolve an object scope through the same central rules as student querysets."""
    if not scope:
        return False

    context = _scope_context(scope)
    cycle = context.get("academic_cycle")
    if (
        cycle is not None
        and codename in WRITE_PERMISSION_CODENAMES
        and getattr(cycle, "status", None) != AcademicCycle.CycleStatus.ACTIVE
    ):
        return False

    student = scope.get("student")
    if student is not None:
        return can_access_student(user=user, codename=codename, student=student, when=when)

    if _teacher_matches_scope(user=user, scope=scope, when=when):
        return True

    return any(
        grant_matches_scope(grant, scope, when=when)
        for grant in active_scope_grants(user=user, codename=codename, when=when)
    )


def teaching_assignment_queryset(*, user, when=None):
    person = getattr(user, "person", None)
    if person is None:
        return TeachingAssignment.objects.none()

    current_date = _local_date(when)
    return TeachingAssignment.objects.filter(
        teacher=person,
        academic_cycle__status=AcademicCycle.CycleStatus.ACTIVE,
        starts_on__lte=current_date,
    ).filter(Q(ends_on__isnull=True) | Q(ends_on__gte=current_date))


def _teacher_matches_scope(*, user, scope, when=None):
    assignments = teaching_assignment_queryset(user=user, when=when)
    teaching_assignment = scope.get("teaching_assignment")
    if teaching_assignment is not None:
        assignment_id = getattr(teaching_assignment, "pk", teaching_assignment)
        return assignments.filter(pk=assignment_id).exists()

    section = scope.get("section")
    subject = scope.get("subject")
    if section is None:
        return False

    assignments = assignments.filter(section_id=getattr(section, "pk", section))
    if subject is not None:
        assignments = assignments.filter(subject_id=getattr(subject, "pk", subject))
    return assignments.exists()


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


#: Modulo cuya administracion cubre el expediente de cualquier estudiante.
STUDENTS_MODULE_KEY = "students"


def _student_filter_for_grant(grant):
    if not grant.has_effective_scope() or grant.subject_id:
        return None

    # Un permiso sobre el modulo de estudiantes alcanza a TODOS los expedientes,
    # tambien a los que aun no tienen matricula. El resto de las dimensiones
    # (institucion, ciclo, grado, seccion) resuelve al estudiante A TRAVES de su
    # matricula, asi que sin ella nadie lo veria: quien acaba de dar de alta a un
    # estudiante no lo encontraria en el listado, y no podria matricularlo porque
    # ni siquiera aparece. La escritura ya usaba este mismo alcance
    # (`student_edit_basic` sobre `module_key="students"`); la lectura solo lo
    # acompana.
    if grant.module_key:
        # `Q(pk__isnull=False)` y no `Q()`: Django trata la Q vacia como
        # elemento neutro al combinar, asi que un `Q(pk__in=[]) | Q()` sigue sin
        # alcanzar a nadie. Hace falta una condicion que si diga "todos".
        return Q(pk__isnull=False) if grant.module_key == STUDENTS_MODULE_KEY else None

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
        conditions &= Q(
            enrolments__is_active=True,
            enrolments__status="active",
        )
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


def _local_date(when):
    if when is None:
        return timezone.localdate()
    if hasattr(when, "hour"):
        return timezone.localdate(when)
    return when
