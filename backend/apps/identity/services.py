import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.signing import salted_hmac
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare

from apps.audit.services import record_event
from apps.common.models import DomainError
from apps.identity.atomic_permissions import ATOMIC_PERMISSION_CODENAMES
from apps.identity.models import ActivationChallenge, Role, RoleAssignment, ScopeGrant

ACCOUNT_DISABLE_PERMISSION = "account_disable"
ACCOUNT_CREATE_PERMISSION = "account_create"
ACCOUNT_ACTIVATE_PERMISSION = "account_activate"
ACTIVATION_CODE_DIGITS = 8
PERMISSION_CATALOG_READ_PERMISSION = "role_assign"


def list_atomic_permissions(*, actor):
    is_authorized = bool(
        actor
        and (actor.is_superuser or actor.has_atomic_permission(PERMISSION_CATALOG_READ_PERMISSION))
    )
    if not is_authorized:
        record_event(
            actor=actor,
            action="identity.permission_catalog.read_denied",
            resource="Permission",
            context={"result": "denied", "reason": "missing_permission"},
        )
        raise PermissionDenied("Actor lacks permission to read the permission catalog.")

    permissions = Permission.objects.filter(
        content_type__app_label="identity",
        content_type__model="role",
        codename__in=ATOMIC_PERMISSION_CODENAMES,
    ).order_by("codename")
    record_event(
        actor=actor,
        action="identity.permission_catalog.read",
        resource="Permission",
        context={"result": "success", "permission_count": permissions.count()},
    )
    return permissions


def _can_manage_roles(actor):
    return bool(
        actor
        and (actor.is_superuser or actor.has_atomic_permission(PERMISSION_CATALOG_READ_PERMISSION))
    )


def _audit_role_denied(*, actor, action, role=None, reason="missing_permission"):
    record_event(
        actor=actor,
        action=f"identity.role.{action}_denied",
        resource="Role",
        resource_identifier=str(role.public_id) if role else "",
        context={"result": "denied", "reason": reason},
    )


def _resolve_atomic_permissions(permission_codenames):
    requested = set(permission_codenames)
    if not requested.issubset(ATOMIC_PERMISSION_CODENAMES):
        raise DomainError("Role permissions must belong to the atomic permission catalog.")

    permissions = list(
        Permission.objects.filter(
            content_type__app_label="identity",
            content_type__model="role",
            codename__in=requested,
        )
    )
    if len(permissions) != len(requested):
        raise DomainError("One or more atomic permissions do not exist.")
    return permissions


def list_roles(*, actor):
    if not _can_manage_roles(actor):
        _audit_role_denied(actor=actor, action="list")
        raise PermissionDenied("Actor lacks permission to read roles.")
    return Role.objects.prefetch_related("permissions").order_by("name")


def create_role(*, actor, name, slug, description="", permission_codenames=()):
    if not _can_manage_roles(actor):
        _audit_role_denied(actor=actor, action="create")
        raise PermissionDenied("Actor lacks permission to create roles.")

    permissions = _resolve_atomic_permissions(permission_codenames)
    with transaction.atomic():
        role = Role.objects.create(name=name, slug=slug, description=description)
        role.permissions.set(permissions)
        record_event(
            actor=actor,
            action="identity.role.created",
            resource="Role",
            resource_identifier=str(role.public_id),
            context={
                "result": "success",
                "role_slug": role.slug,
                "permissions": sorted(permission_codenames),
            },
        )
    return role


def update_role(*, actor, role, name=None, description=None, permission_codenames=None):
    if not _can_manage_roles(actor):
        _audit_role_denied(actor=actor, action="update", role=role)
        raise PermissionDenied("Actor lacks permission to update roles.")
    protect_system_role(actor=actor, role=role)

    permissions = None
    if permission_codenames is not None:
        permissions = _resolve_atomic_permissions(permission_codenames)

    with transaction.atomic():
        locked_role = Role.objects.select_for_update().get(pk=role.pk)
        before = {
            "name": locked_role.name,
            "description": locked_role.description,
            "permissions": sorted(locked_role.permissions.values_list("codename", flat=True)),
        }
        update_fields = []
        if name is not None and name != locked_role.name:
            locked_role.name = name
            update_fields.append("name")
        if description is not None and description != locked_role.description:
            locked_role.description = description
            update_fields.append("description")
        if update_fields:
            locked_role.save(update_fields=[*update_fields, "updated_at"])
        if permissions is not None:
            locked_role.permissions.set(permissions)

        after = {
            "name": locked_role.name,
            "description": locked_role.description,
            "permissions": sorted(locked_role.permissions.values_list("codename", flat=True)),
        }
        record_event(
            actor=actor,
            action="identity.role.updated",
            resource="Role",
            resource_identifier=str(locked_role.public_id),
            context={"result": "success", "before": before, "after": after},
        )
    return locked_role


class InvalidCredentialsError(Exception):
    pass


class AccountTemporarilyLockedError(Exception):
    pass


class InvalidActivationChallengeError(DomainError):
    pass


class ActivationPasswordError(DomainError):
    pass


def _can_create_account(actor):
    return bool(
        actor and (actor.is_superuser or actor.has_atomic_permission(ACCOUNT_CREATE_PERMISSION))
    )


def _audit_account_create_denied(*, actor, person):
    record_event(
        actor=actor,
        action="identity.account.create_denied",
        resource="UserAccount",
        context={
            "person_id": getattr(person, "pk", None),
            "result": "denied",
            "reason": "missing_permission",
        },
    )


def create_account(*, actor, person, username, email=""):
    is_authorized = _can_create_account(actor)
    if not is_authorized:
        _audit_account_create_denied(actor=actor, person=person)
        raise PermissionDenied("Actor lacks permission to create accounts.")

    if person is None:
        raise DomainError("An institutional person is required.")
    if hasattr(person, "user_account"):
        raise DomainError("The institutional person already has an account.")

    user_model = get_user_model()
    with transaction.atomic():
        account = user_model.objects.create_user(
            username=username,
            email=email or person.email,
            person=person,
            status=user_model.AccountStatus.PENDING,
            is_active=False,
            password=None,
        )
        record_event(
            actor=actor,
            action="identity.account.created",
            resource="UserAccount",
            resource_identifier=str(account.pk),
            context={
                "target_user_id": account.pk,
                "person_id": person.pk,
                "status": account.status,
                "result": "success",
            },
        )
    return account


def _activation_code_digest(code):
    return salted_hmac(
        "identity.activation_challenge",
        code,
        algorithm="sha256",
    ).hexdigest()


def _generate_activation_code():
    return f"{secrets.randbelow(10**ACTIVATION_CODE_DIGITS):0{ACTIVATION_CODE_DIGITS}d}"


def _issue_activation_challenge(*, actor, account, reason):
    if account.status != account.AccountStatus.PENDING or account.is_active:
        raise DomainError("Activation challenges require a pending inactive account.")

    now = timezone.now()
    ActivationChallenge.objects.filter(
        account=account,
        is_active=True,
        used_at__isnull=True,
        revoked_at__isnull=True,
    ).update(is_active=False, revoked_at=now, updated_at=now)

    code = _generate_activation_code()
    challenge = ActivationChallenge.objects.create(
        account=account,
        token_digest=_activation_code_digest(code),
        expires_at=now + timedelta(minutes=settings.ACCOUNT_ACTIVATION_TTL_MINUTES),
    )
    record_event(
        actor=actor,
        action="identity.activation_challenge.issued",
        resource="ActivationChallenge",
        resource_identifier=str(challenge.public_id),
        context={
            "target_user_id": account.pk,
            "challenge_id": str(challenge.public_id),
            "expires_at": challenge.expires_at.isoformat(),
            "max_attempts": settings.ACCOUNT_ACTIVATION_MAX_ATTEMPTS,
            "reason": reason,
            "result": "success",
        },
    )
    return challenge, code


def provision_account_with_activation(*, actor, person, username, email=""):
    if not _can_create_account(actor):
        _audit_account_create_denied(actor=actor, person=person)
        raise PermissionDenied("Actor lacks permission to create accounts.")

    with transaction.atomic():
        account = create_account(
            actor=actor,
            person=person,
            username=username,
            email=email,
        )
        challenge, code = _issue_activation_challenge(
            actor=actor,
            account=account,
            reason="initial_provisioning",
        )
        return account, challenge, code


def reissue_activation_challenge(*, actor, account):
    is_authorized = bool(
        actor and (actor.is_superuser or actor.has_atomic_permission(ACCOUNT_ACTIVATE_PERMISSION))
    )
    if not is_authorized:
        record_event(
            actor=actor,
            action="identity.activation_challenge.issue_denied",
            resource="UserAccount",
            resource_identifier=str(account.pk),
            context={
                "target_user_id": account.pk,
                "result": "denied",
                "reason": "missing_permission",
            },
        )
        raise PermissionDenied("Actor lacks permission to issue activation challenges.")

    with transaction.atomic():
        locked_account = account.__class__.objects.select_for_update().get(pk=account.pk)
        return _issue_activation_challenge(
            actor=actor,
            account=locked_account,
            reason="administrative_reissue",
        )


def _audit_activation_denied(*, account, challenge=None, reason, failed_attempts=None):
    context = {
        "result": "denied",
        "reason": reason,
    }
    if account:
        context["target_user_id"] = account.pk
    if challenge:
        context["challenge_id"] = str(challenge.public_id)
    if failed_attempts is not None:
        context["failed_attempts"] = failed_attempts
    record_event(
        actor=None,
        action="identity.activation_challenge.denied",
        resource="ActivationChallenge",
        resource_identifier=str(challenge.public_id) if challenge else "",
        context=context,
    )


def activate_account(*, username, activation_code, password):
    user_model = get_user_model()
    account_id = user_model.objects.filter(username=username).values_list("pk", flat=True).first()
    if account_id is None:
        _audit_activation_denied(account=None, reason="account_not_found")
        raise InvalidActivationChallengeError("Código de activación inválido o vencido.")

    error = None
    activated_account = None
    with transaction.atomic():
        account = user_model.objects.select_for_update().get(pk=account_id)
        challenge = account.activation_challenges.select_for_update().first()
        now = timezone.now()

        unusable_reason = None
        if account.status != account.AccountStatus.PENDING or account.is_active:
            unusable_reason = "account_not_pending"
        elif challenge is None:
            unusable_reason = "challenge_not_found"
        elif challenge.used_at is not None:
            unusable_reason = "already_used"
        elif challenge.revoked_at is not None or not challenge.is_active:
            unusable_reason = "revoked"
        elif challenge.expires_at <= now:
            unusable_reason = "expired"
        elif challenge.failed_attempts >= settings.ACCOUNT_ACTIVATION_MAX_ATTEMPTS:
            unusable_reason = "attempts_exhausted"

        if unusable_reason:
            _audit_activation_denied(
                account=account,
                challenge=challenge,
                reason=unusable_reason,
                failed_attempts=getattr(challenge, "failed_attempts", None),
            )
            error = InvalidActivationChallengeError("Código de activación inválido o vencido.")
        elif not constant_time_compare(
            challenge.token_digest,
            _activation_code_digest(activation_code),
        ):
            challenge.failed_attempts += 1
            challenge.save(update_fields=["failed_attempts", "updated_at"])
            _audit_activation_denied(
                account=account,
                challenge=challenge,
                reason="invalid_code",
                failed_attempts=challenge.failed_attempts,
            )
            error = InvalidActivationChallengeError("Código de activación inválido o vencido.")
        else:
            try:
                validate_password(password, user=account)
            except ValidationError as exc:
                _audit_activation_denied(
                    account=account,
                    challenge=challenge,
                    reason="password_policy",
                    failed_attempts=challenge.failed_attempts,
                )
                error = ActivationPasswordError(" ".join(exc.messages))
            else:
                account.set_password(password)
                account.status = account.AccountStatus.ACTIVE
                account.is_active = True
                account.failed_login_attempts = 0
                account.locked_until = None
                account.save(
                    update_fields=[
                        "password",
                        "status",
                        "is_active",
                        "failed_login_attempts",
                        "locked_until",
                    ]
                )
                challenge.used_at = now
                challenge.is_active = False
                challenge.save(update_fields=["used_at", "is_active", "updated_at"])
                record_event(
                    actor=account,
                    action="identity.account.activated",
                    resource="UserAccount",
                    resource_identifier=str(account.pk),
                    context={
                        "target_user_id": account.pk,
                        "challenge_id": str(challenge.public_id),
                        "result": "success",
                    },
                )
                activated_account = account

    if error:
        raise error
    return activated_account


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
    if not _can_manage_roles(actor):
        record_event(
            actor=actor,
            action="identity.role_assignment.create_denied",
            resource="UserAccount",
            resource_identifier=str(user.pk),
            context={"result": "denied", "reason": "missing_permission"},
        )
        raise PermissionDenied("Actor lacks permission to assign roles.")
    if actor.pk == user.pk:
        record_event(
            actor=actor,
            action="identity.role_assignment.create_denied",
            resource="UserAccount",
            resource_identifier=str(user.pk),
            context={"result": "denied", "reason": "self_escalation"},
        )
        raise PermissionDenied("Users cannot assign roles to themselves.")

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


def revoke_role_assignment(*, actor, assignment, ends_at=None):
    if not _can_manage_roles(actor):
        record_event(
            actor=actor,
            action="identity.role_assignment.revoke_denied",
            resource="RoleAssignment",
            resource_identifier=str(assignment.public_id),
            context={"result": "denied", "reason": "missing_permission"},
        )
        raise PermissionDenied("Actor lacks permission to revoke role assignments.")
    if actor.pk == assignment.user_id:
        record_event(
            actor=actor,
            action="identity.role_assignment.revoke_denied",
            resource="RoleAssignment",
            resource_identifier=str(assignment.public_id),
            context={"result": "denied", "reason": "self_escalation"},
        )
        raise PermissionDenied("Users cannot revoke their own roles.")

    effective_end = ends_at or timezone.now()
    with transaction.atomic():
        locked_assignment = RoleAssignment.objects.select_for_update().get(pk=assignment.pk)
        previous_end = locked_assignment.ends_at
        locked_assignment.ends_at = effective_end
        locked_assignment.save(update_fields=["ends_at", "updated_at"])
        record_event(
            actor=actor,
            action="identity.role_assignment.revoked",
            resource="RoleAssignment",
            resource_identifier=str(locked_assignment.public_id),
            context={
                "result": "success",
                "target_user_id": locked_assignment.user_id,
                "role_slug": locked_assignment.role.slug,
                "before_ends_at": previous_end.isoformat() if previous_end else None,
                "after_ends_at": effective_end.isoformat(),
            },
        )
    return locked_assignment


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
