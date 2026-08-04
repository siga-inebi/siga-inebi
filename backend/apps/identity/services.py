from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.common.models import DomainError
from apps.identity.models import RoleAssignment, ScopeGrant

ACCOUNT_DISABLE_PERMISSION = "account_disable"


class InvalidCredentialsError(Exception):
    pass


class AccountTemporarilyLockedError(Exception):
    pass


def _audit_login_denied(*, account, reason, failed_attempts=None, locked_until=None):
    context = {"result": "denied", "reason": reason}
    if failed_attempts is not None:
        context["failed_attempts"] = failed_attempts
    if locked_until is not None:
        context["locked_until"] = locked_until.isoformat()

    record_event(
        actor=None,
        action="identity.login.denied",
        resource="UserAccount",
        resource_identifier=str(account.pk) if account else "",
        context=context,
    )


def authenticate_account(*, request, username, password):
    user_model = get_user_model()
    account = user_model.objects.filter(username=username).first()

    if account and account.is_locked():
        _audit_login_denied(
            account=account,
            reason="temporarily_locked",
            failed_attempts=account.failed_login_attempts,
            locked_until=account.locked_until,
        )
        raise AccountTemporarilyLockedError

    user = authenticate(request=request, username=username, password=password)
    if user is None:
        if not account or not account.is_active:
            _audit_login_denied(account=account, reason="invalid_credentials")
            raise InvalidCredentialsError

        with transaction.atomic():
            account = user_model.objects.select_for_update().get(pk=account.pk)
            if account.locked_until and account.locked_until <= timezone.now():
                account.failed_login_attempts = 0
                account.locked_until = None

            account.failed_login_attempts += 1
            if account.failed_login_attempts >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
                account.locked_until = timezone.now() + timedelta(
                    minutes=settings.LOGIN_LOCKOUT_MINUTES
                )
            account.save(update_fields=["failed_login_attempts", "locked_until"])

            _audit_login_denied(
                account=account,
                reason=("temporarily_locked" if account.is_locked() else "invalid_credentials"),
                failed_attempts=account.failed_login_attempts,
                locked_until=account.locked_until,
            )

        if account.is_locked():
            raise AccountTemporarilyLockedError
        raise InvalidCredentialsError

    if user.failed_login_attempts or user.locked_until:
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=["failed_login_attempts", "locked_until"])
    return user


def assign_role(
    *,
    actor,
    user,
    role,
    starts_at=None,
    ends_at=None,
    scope=None,
):
    if actor and actor.pk == user.pk:
        raise PermissionDenied("Users cannot assign roles to themselves.")
    if actor and not (actor.is_superuser or actor.has_atomic_permission("role_assign")):
        raise PermissionDenied("Actor lacks permission to assign roles.")

    assignment, created = RoleAssignment.objects.get_or_create(
        user=user,
        role=role,
        starts_at=starts_at or timezone.now(),
        defaults={"ends_at": ends_at},
    )
    if not created and ends_at != assignment.ends_at:
        assignment.ends_at = ends_at
        assignment.save(update_fields=["ends_at", "updated_at"])

    if scope:
        ScopeGrant.objects.get_or_create(
            assignment=assignment,
            starts_at=scope.get("starts_at") or timezone.now(),
            defaults={
                "ends_at": scope.get("ends_at"),
                "institution": scope.get("institution"),
                "academic_cycle": scope.get("academic_cycle"),
                "grade": scope.get("grade"),
                "section": scope.get("section"),
                "subject": scope.get("subject"),
                "teaching_assignment": scope.get("teaching_assignment"),
                "student": scope.get("student"),
                "module_key": scope.get("module_key", ""),
            },
        )

    record_event(
        actor=actor,
        action="identity.role_assignment.created",
        resource="RoleAssignment",
        resource_identifier=str(assignment.pk),
        context={
            "target_user_id": user.pk,
            "role_slug": role.slug,
        },
    )
    return assignment


def protect_system_role(*, actor, role):
    if role.is_system and not getattr(actor, "is_superuser", False):
        raise DomainError("System roles require elevated authorization.")
    return role


def disable_account(*, actor, user):
    is_authorized = bool(
        actor and (actor.is_superuser or actor.has_atomic_permission(ACCOUNT_DISABLE_PERMISSION))
    )
    if not is_authorized:
        record_event(
            actor=actor,
            action="identity.account.disable_denied",
            resource="UserAccount",
            resource_identifier=str(user.pk),
            context={
                "target_user_id": user.pk,
                "result": "denied",
            },
        )
        raise PermissionDenied("Actor lacks permission to disable accounts.")

    with transaction.atomic():
        account = user.__class__.objects.select_for_update().get(pk=user.pk)
        previous_state = {
            "status": account.status,
            "is_active": account.is_active,
        }
        account.status = account.AccountStatus.DISABLED
        account.is_active = False
        account.save(update_fields=["status", "is_active"])

        record_event(
            actor=actor,
            action="identity.account.disabled",
            resource="UserAccount",
            resource_identifier=str(account.pk),
            context={
                "target_user_id": account.pk,
                "before": previous_state,
                "after": {
                    "status": account.status,
                    "is_active": account.is_active,
                },
                "result": "success",
            },
        )
        return account
