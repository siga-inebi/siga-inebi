"""Read-side queries for identity and authorization administration."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Prefetch, Q
from django.utils import timezone

from apps.common.exceptions import ResourceNotFoundError
from apps.identity.models import Role, RoleAssignment, ScopeGrant
from apps.people.models import Person

SCOPE_GRANT_RELATED = (
    "institution",
    "academic_cycle",
    "grade",
    "section__offering__grade",
    "subject",
    "teaching_assignment__subject",
    "teaching_assignment__section__offering__grade",
    "student__person",
)

#: Ordenes admitidos en el listado de cuentas (`?ordering=`).
ACCOUNT_ORDERINGS = {
    "username": ("username",),
    "-username": ("-username",),
    "last_login": ("last_login", "username"),
    "-last_login": ("-last_login", "username"),
    "person": ("person__first_name", "person__last_name"),
    "-person": ("-person__first_name", "-person__last_name"),
}


def role_or_404(public_id):
    try:
        return Role.objects.get(public_id=public_id)
    except (Role.DoesNotExist, ValueError, TypeError) as exc:
        raise ResourceNotFoundError("No se encontró el rol.") from exc


def account_or_404(public_id):
    try:
        return get_user_model().objects.select_related("person").get(public_id=public_id)
    except (get_user_model().DoesNotExist, ValueError, TypeError) as exc:
        raise ResourceNotFoundError("No se encontró la cuenta.") from exc


def role_assignment_or_404(public_id):
    try:
        return RoleAssignment.objects.select_related("role", "user").get(public_id=public_id)
    except (RoleAssignment.DoesNotExist, ValueError, TypeError) as exc:
        raise ResourceNotFoundError("No se encontró la asignación de rol.") from exc


def person_or_404(public_id):
    try:
        return Person.objects.get(public_id=public_id)
    except (Person.DoesNotExist, ValueError, TypeError) as exc:
        raise ResourceNotFoundError("No se encontró la persona.") from exc


def _current_assignments_prefetch(when=None):
    when = when or timezone.now()
    return Prefetch(
        "role_assignments",
        queryset=RoleAssignment.objects.active_at(when)
        .filter(is_active=True)
        .select_related("role")
        .order_by("role__name"),
        to_attr="current_assignments",
    )


def accounts(*, status=None, search=None, role=None, locked=None, ordering=None):
    """
    U4: listado de cuentas con buscador (usuario, nombre, apellido, correo),
    filtro por estado, por rol vigente y por bloqueo temporal, y orden.
    """
    queryset = (
        get_user_model()
        .objects.select_related("person")
        .prefetch_related(_current_assignments_prefetch())
    )
    if status:
        queryset = queryset.filter(status=status)
    if search:
        queryset = queryset.filter(
            Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(person__first_name__icontains=search)
            | Q(person__last_name__icontains=search)
        )
    if role:
        now = timezone.now()
        queryset = queryset.filter(
            role_assignments__in=RoleAssignment.objects.active_at(now).filter(
                is_active=True, role__public_id=role
            )
        ).distinct()
    if locked is True:
        queryset = queryset.filter(locked_until__gt=timezone.now())
    return queryset.order_by(*ACCOUNT_ORDERINGS.get(ordering or "", ("username",)))


def account_detail(public_id):
    account = account_or_404(public_id)
    return (
        get_user_model()
        .objects.select_related("person")
        .prefetch_related(_current_assignments_prefetch())
        .get(pk=account.pk)
    )


def role_assignments_for_account(account):
    """U5/RA2: todas las asignaciones de la cuenta, vigentes e historicas."""
    return (
        RoleAssignment.objects.filter(user=account)
        .select_related("role")
        .prefetch_related(
            Prefetch(
                "scope_grants",
                queryset=ScopeGrant.objects.select_related(*SCOPE_GRANT_RELATED),
            )
        )
        .order_by("-starts_at")
    )


def current_role_assignments(user, *, when=None):
    """MC1: roles vigentes de la cuenta con sus alcances vigentes."""
    when = when or timezone.now()
    return (
        RoleAssignment.objects.active_at(when)
        .filter(user=user, is_active=True, role__is_active=True)
        .select_related("role")
        .prefetch_related(
            Prefetch(
                "scope_grants",
                queryset=ScopeGrant.objects.filter(is_active=True, starts_at__lte=when)
                .filter(Q(ends_at__isnull=True) | Q(ends_at__gte=when))
                .select_related(*SCOPE_GRANT_RELATED),
            )
        )
        .order_by("role__name")
    )


def roles(*, include_inactive=True):
    """RO1: roles con su composicion y cuantas cuentas los tienen vigentes."""
    now = timezone.now()
    queryset = Role.objects.prefetch_related("permissions").annotate(
        active_account_count=Count(
            "assignments__user",
            filter=Q(assignments__is_active=True, assignments__starts_at__lte=now)
            & (Q(assignments__ends_at__isnull=True) | Q(assignments__ends_at__gte=now)),
            distinct=True,
        )
    )
    if not include_inactive:
        queryset = queryset.filter(is_active=True)
    return queryset.order_by("name")


def role_holders(role, *, when=None):
    """RO5: asignaciones vigentes de un rol, con su cuenta."""
    when = when or timezone.now()
    return (
        RoleAssignment.objects.active_at(when)
        .filter(role=role, is_active=True)
        .select_related("user__person", "role")
        .order_by("user__username")
    )


def permission_holders(codename, *, when=None):
    """RO5: "quien tiene este permiso" -- asignaciones vigentes de roles activos que lo dan."""
    when = when or timezone.now()
    return (
        RoleAssignment.objects.active_at(when)
        .filter(is_active=True, role__is_active=True, role__permissions__codename=codename)
        .select_related("user__person", "role")
        .order_by("user__username", "role__name")
        .distinct()
    )


def expiring_role_assignments(*, days, expired_days=30, when=None):
    """
    RA5: asignaciones que vencen dentro de ``days`` dias y las que vencieron en
    los ultimos ``expired_days``, para que nadie pierda acceso sin aviso al
    cambiar de ciclo.
    """
    when = when or timezone.now()
    return (
        RoleAssignment.objects.filter(
            is_active=True,
            ends_at__isnull=False,
            ends_at__gte=when - timedelta(days=expired_days),
            ends_at__lte=when + timedelta(days=days),
            starts_at__lte=when,
        )
        .select_related("user__person", "role")
        .order_by("ends_at")
    )


def account_candidates(*, search=None):
    """
    U1/D10: personas registradas que todavia no tienen cuenta, buscables por
    nombre, apellido, CUI o correo, para dar acceso sin crear duplicados.
    """
    queryset = (
        Person.objects.filter(user_account__isnull=True)
        .select_related("teacher_profile", "student_profile", "guardian_profile")
        .order_by("first_name", "last_name")
    )
    if search:
        term = search.strip()
        condition = (
            Q(first_name__icontains=term)
            | Q(last_name__icontains=term)
            | Q(email__icontains=term)
            | Q(cui=term.replace(" ", ""))
        )
        words = term.split()
        if len(words) > 1:
            # "Ana López": primer nombre y apellido en sus propias columnas.
            condition |= Q(first_name__icontains=words[0]) & Q(last_name__icontains=words[-1])
        queryset = queryset.filter(condition)
    return queryset


def pending_activation_expiry(account):
    """U2/U5: vencimiento del codigo de activacion pendiente, si hay uno."""
    return (
        account.activation_challenges.filter(
            is_active=True, used_at__isnull=True, revoked_at__isnull=True
        )
        .order_by("-created_at")
        .values_list("expires_at", flat=True)
        .first()
    )
