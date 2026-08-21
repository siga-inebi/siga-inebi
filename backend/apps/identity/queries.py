"""Read-side queries for identity and authorization administration."""

from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.common.exceptions import ResourceNotFoundError
from apps.identity.models import Role, RoleAssignment


def role_or_404(public_id):
    try:
        return Role.objects.get(public_id=public_id)
    except (Role.DoesNotExist, ValueError, TypeError) as exc:
        raise ResourceNotFoundError("Role not found.") from exc


def account_or_404(account_id):
    try:
        return get_user_model().objects.select_related("person").get(pk=account_id)
    except get_user_model().DoesNotExist as exc:
        raise ResourceNotFoundError("Account not found.") from exc


def role_assignment_or_404(public_id):
    try:
        return RoleAssignment.objects.select_related("role").get(public_id=public_id)
    except (RoleAssignment.DoesNotExist, ValueError, TypeError) as exc:
        raise ResourceNotFoundError("Role assignment not found.") from exc


def accounts(*, status=None, search=None):
    queryset = get_user_model().objects.select_related("person").order_by("username")
    if status:
        queryset = queryset.filter(status=status)
    if search:
        queryset = queryset.filter(
            Q(username__icontains=search)
            | Q(person__first_name__icontains=search)
            | Q(person__last_name__icontains=search)
        )
    return queryset
