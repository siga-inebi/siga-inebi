import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, update_session_auth_hash
from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.core.signing import salted_hmac
from django.db import models, transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.text import slugify

from apps.audit.services import record_event
from apps.common.exceptions import AuthorizationError, DomainError, FieldValidationError
from apps.identity import queries, scopes
from apps.identity.atomic_permissions import (
    ATOMIC_PERMISSION_CODENAMES,
    ATOMIC_PERMISSION_CODES_BY_CODENAME,
    ATOMIC_PERMISSIONS,
)
from apps.identity.models import (
    ActivationChallenge,
    PasswordResetChallenge,
    Role,
    RoleAssignment,
    ScopeGrant,
)

ACCOUNT_DISABLE_PERMISSION = "account_disable"
ACCOUNT_CREATE_PERMISSION = "account_create"
ACCOUNT_ACTIVATE_PERMISSION = "account_activate"
PASSWORD_RESET_TTL_MINUTES = 30
ACTIVATION_CODE_DIGITS = 8
PERMISSION_CATALOG_READ_PERMISSION = "role_assign"
IDENTITY_ADMIN_SCOPE = {"module_key": "identity"}
SCOPE_DIMENSIONS = {
    "institution",
    "academic_cycle",
    "grade",
    "section",
    "subject",
    "teaching_assignment",
    "student",
}

#: RA4: alcance "sus asignaciones docentes vigentes" (ver ``assign_role``).
TEACHING_ASSIGNMENTS_SCOPE_KEY = "teaching_assignments"

#: Modulos que un alcance puede nombrar con ``module_key``, con su etiqueta.
#: Son los que alguna vista o servicio evalua de verdad; ofrecer otros seria
#: crear alcances que no autorizan nada.
SCOPE_MODULES = (
    ("identity", "Administración de cuentas y accesos"),
    ("students", "Expedientes de estudiantes"),
    ("teachers", "Expedientes docentes"),
    ("enrolments", "Matrícula"),
    (TEACHING_ASSIGNMENTS_SCOPE_KEY, "Sus asignaciones docentes vigentes"),
)
SCOPE_MODULE_LABELS = dict(SCOPE_MODULES)

#: RA5: horizonte de aviso de asignaciones por vencer.
EXPIRING_ASSIGNMENT_DAYS = 15


def _has_identity_permission(actor, codename):
    return bool(
        actor
        and (
            actor.is_superuser or actor.has_scoped_permission(codename, scope=IDENTITY_ADMIN_SCOPE)
        )
    )


def require_all_permissions(
    *, actor, permission_codenames, denial_action, denial_resource="", denial_resource_identifier=""
):
    """
    Composite authorization: ``actor`` must hold every codename in
    ``permission_codenames``, not just one of them (RF-ASI-006 — a capture
    attempt needs permission for both its movement type and its capture
    mode). Missing any of them denies the whole attempt and records an
    auditable rejection, never a silent failure: permission composition is
    identity's concern, the caller only supplies which codenames apply and
    where to file the denial.
    """
    if all(actor.has_atomic_permission(codename) for codename in permission_codenames):
        return
    record_event(
        actor=actor,
        action=denial_action,
        resource=denial_resource,
        resource_identifier=denial_resource_identifier,
        context={"result": "denied", "permissions_required": list(permission_codenames)},
    )
    raise AuthorizationError("El actor no tiene los permisos requeridos para esta operacion.")


def filter_queryset_by_scope(*, actor, codename, queryset, dimension, lookup, when=None):
    if dimension not in SCOPE_DIMENSIONS:
        raise DomainError("Dimension de alcance no soportada.")
    when = when or timezone.now()
    allowed_ids = ScopeGrant.objects.filter(
        assignment__in=RoleAssignment.objects.active_at(when).filter(
            user=actor,
            role__permissions__codename=codename,
        ),
        is_active=True,
        starts_at__lte=when,
    ).filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=when))
    allowed_ids = allowed_ids.exclude(**{f"{dimension}_id__isnull": True}).values_list(
        f"{dimension}_id", flat=True
    )
    return queryset.filter(**{f"{lookup}__in": allowed_ids}).distinct()


def list_atomic_permissions(*, actor):
    is_authorized = bool(_has_identity_permission(actor, PERMISSION_CATALOG_READ_PERMISSION))
    if not is_authorized:
        record_event(
            actor=actor,
            action="identity.permission_catalog.read_denied",
            resource="Permission",
            context={"result": "denied", "reason": "missing_permission"},
        )
        raise AuthorizationError(
            "El actor no tiene permiso para consultar el catalogo de permisos."
        )

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
    return _has_identity_permission(actor, PERMISSION_CATALOG_READ_PERMISSION)


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
        raise DomainError(
            "Los permisos de un rol deben pertenecer al catalogo de permisos atomicos."
        )

    permissions = list(
        Permission.objects.filter(
            content_type__app_label="identity",
            content_type__model="role",
            codename__in=requested,
        )
    )
    if len(permissions) != len(requested):
        raise DomainError("Uno o mas permisos atomicos no existen.")
    return permissions


def _active_account_administrators(*, when=None):
    when = when or timezone.now()
    return (
        RoleAssignment.objects.active_at(when)
        .filter(
            role__permissions__codename=ACCOUNT_CREATE_PERMISSION,
            user__is_active=True,
            user__status=get_user_model().AccountStatus.ACTIVE,
            scope_grants__is_active=True,
            scope_grants__starts_at__lte=when,
        )
        .filter(
            models.Q(scope_grants__ends_at__isnull=True) | models.Q(scope_grants__ends_at__gte=when)
        )
        .distinct()
    )


def _ensure_account_administrator_remains(*, assignment=None, role=None, user=None):
    administrators = _active_account_administrators()
    if assignment is not None:
        administrators = administrators.exclude(pk=assignment.pk)
    if role is not None:
        administrators = administrators.exclude(role=role)
    if user is not None:
        administrators = administrators.exclude(user=user)
    if not administrators.exists():
        raise DomainError("No se puede quitar al ultimo administrador de cuentas.")


def list_roles(*, actor, include_inactive=True):
    if not _can_manage_roles(actor):
        _audit_role_denied(actor=actor, action="list")
        raise AuthorizationError("El actor no tiene permiso para consultar roles.")
    return queries.roles(include_inactive=include_inactive)


def suggest_role_slug(name, *, exclude_pk=None):
    """
    RO3: el ``slug`` se deriva del nombre en vez de escribirse a mano. Si ya
    existe, se numera (``docente-2``) para que dos roles con nombres parecidos
    no choquen con el indice unico al guardar.
    """
    base = slugify(name)[:140] or "rol"
    candidate = base
    suffix = 2
    existing = Role.objects.all()
    if exclude_pk is not None:
        existing = existing.exclude(pk=exclude_pk)
    while existing.filter(slug=candidate).exists():
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def create_role(
    *,
    actor,
    name,
    slug=None,
    description="",
    permission_codenames=(),
    session_idle_timeout_minutes=None,
):
    if not _can_manage_roles(actor):
        _audit_role_denied(actor=actor, action="create")
        raise AuthorizationError("El actor no tiene permiso para crear roles.")
    if Role.objects.filter(name__iexact=name).exists():
        raise DomainError("Ya existe un rol con ese nombre.")
    if slug and Role.objects.filter(slug=slug).exists():
        raise DomainError("Ya existe un rol con ese identificador.")
    slug = slug or suggest_role_slug(name)

    timeout_minutes = (
        settings.DEFAULT_SESSION_IDLE_TIMEOUT_MINUTES
        if session_idle_timeout_minutes is None
        else session_idle_timeout_minutes
    )
    if timeout_minutes < 1:
        raise DomainError("La duración de inactividad debe ser de al menos un minuto.")
    permissions = _resolve_atomic_permissions(permission_codenames)
    with transaction.atomic():
        role = Role.objects.create(
            name=name,
            slug=slug,
            description=description,
            session_idle_timeout_minutes=timeout_minutes,
        )
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
                "session_idle_timeout_minutes": role.session_idle_timeout_minutes,
            },
        )
    return role


def update_role(
    *,
    actor,
    role,
    name=None,
    description=None,
    permission_codenames=None,
    session_idle_timeout_minutes=None,
):
    if not _can_manage_roles(actor):
        _audit_role_denied(actor=actor, action="update", role=role)
        raise AuthorizationError("El actor no tiene permiso para modificar roles.")
    protect_system_role(actor=actor, role=role)

    if (
        name is not None
        and name != role.name
        and Role.objects.filter(name__iexact=name).exclude(pk=role.pk).exists()
    ):
        raise DomainError("Ya existe un rol con ese nombre.")

    permissions = None
    if permission_codenames is not None:
        permissions = _resolve_atomic_permissions(permission_codenames)
        currently_administers_accounts = role.permissions.filter(
            codename=ACCOUNT_CREATE_PERMISSION
        ).exists()
        will_administer_accounts = ACCOUNT_CREATE_PERMISSION in permission_codenames
        if currently_administers_accounts and not will_administer_accounts:
            _ensure_account_administrator_remains(role=role)

    with transaction.atomic():
        locked_role = Role.objects.select_for_update().get(pk=role.pk)
        before = {
            "name": locked_role.name,
            "description": locked_role.description,
            "session_idle_timeout_minutes": locked_role.session_idle_timeout_minutes,
            "permissions": sorted(locked_role.permissions.values_list("codename", flat=True)),
        }
        update_fields = []
        if name is not None and name != locked_role.name:
            locked_role.name = name
            update_fields.append("name")
        if description is not None and description != locked_role.description:
            locked_role.description = description
            update_fields.append("description")
        if (
            session_idle_timeout_minutes is not None
            and session_idle_timeout_minutes != locked_role.session_idle_timeout_minutes
        ):
            locked_role.session_idle_timeout_minutes = session_idle_timeout_minutes
            update_fields.append("session_idle_timeout_minutes")
        if update_fields:
            locked_role.save(update_fields=[*update_fields, "updated_at"])
        if permissions is not None:
            locked_role.permissions.set(permissions)

        after = {
            "name": locked_role.name,
            "description": locked_role.description,
            "session_idle_timeout_minutes": locked_role.session_idle_timeout_minutes,
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
    """L5: lleva ``locked_until`` para que el login diga hasta cuando dura el bloqueo."""

    def __init__(self, locked_until=None):
        super().__init__("Cuenta bloqueada temporalmente.")
        self.locked_until = locked_until


class InvalidActivationChallengeError(DomainError):
    pass


class ActivationPasswordError(FieldValidationError):
    """MC2: cada regla incumplida viaja como error del campo ``password``."""


def _can_create_account(actor):
    return _has_identity_permission(actor, ACCOUNT_CREATE_PERMISSION)


def _audit_account_create_denied(*, actor, person, reason="missing_permission"):
    record_event(
        actor=actor,
        action="identity.account.create_denied",
        resource="UserAccount",
        context={
            "person_id": getattr(person, "pk", None),
            "result": "denied",
            "reason": reason,
        },
    )


def _ensure_account_person_is_eligible(*, person, account_kind):
    if person is None:
        raise DomainError("Se requiere una persona institucional.")
    if account_kind not in {"institutional", "guardian"}:
        raise DomainError("El tipo de cuenta indicado no es válido.")
    if account_kind == "guardian":
        guardian = getattr(person, "guardian_profile", None)
        if guardian is None or not guardian.is_active:
            raise DomainError(
                "La persona debe registrarse primero como encargado antes de recibir "
                "una cuenta de encargado."
            )


def create_account(*, actor, person, username, email="", account_kind="institutional"):
    is_authorized = _can_create_account(actor)
    if not is_authorized:
        _audit_account_create_denied(actor=actor, person=person)
        raise AuthorizationError("El actor no tiene permiso para crear cuentas.")

    try:
        _ensure_account_person_is_eligible(person=person, account_kind=account_kind)
    except DomainError:
        _audit_account_create_denied(
            actor=actor,
            person=person,
            reason=("guardian_not_registered" if account_kind == "guardian" else "person_required"),
        )
        raise
    if hasattr(person, "user_account"):
        raise DomainError("Esa persona institucional ya tiene cuenta.")

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
                "account_kind": account_kind,
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
        raise DomainError("Los desafios de activacion requieren una cuenta pendiente e inactiva.")

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


def provision_account_with_activation(
    *, actor, person, username, email="", account_kind="institutional"
):
    if not _can_create_account(actor):
        _audit_account_create_denied(actor=actor, person=person)
        raise AuthorizationError("El actor no tiene permiso para crear cuentas.")

    with transaction.atomic():
        account = create_account(
            actor=actor,
            person=person,
            username=username,
            email=email,
            account_kind=account_kind,
        )
        challenge, code = _issue_activation_challenge(
            actor=actor,
            account=account,
            reason="initial_provisioning",
        )
        return account, challenge, code


def reissue_activation_challenge(*, actor, account):
    is_authorized = bool(_has_identity_permission(actor, ACCOUNT_ACTIVATE_PERMISSION))
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
        raise AuthorizationError("El actor no tiene permiso para emitir desafios de activacion.")
    if actor.pk == account.pk:
        record_event(
            actor=actor,
            action="identity.activation_challenge.issue_denied",
            resource="UserAccount",
            resource_identifier=str(account.pk),
            context={
                "target_user_id": account.pk,
                "result": "denied",
                "reason": "self_activation",
            },
        )
        raise AuthorizationError("Nadie puede reemitir su propio desafio de activacion.")

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
                error = ActivationPasswordError({"password": exc.messages})
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


def _audit_login_lockout_cleared(*, account, cleared_attempts):
    """
    A successful login cleared stale lockout state left over from earlier
    failed attempts. That write went unaudited before RF-BIT-001 -- every
    other branch of ``authenticate_account`` was already covered by
    ``_audit_login_denied``.
    """
    record_event(
        actor=account,
        action="identity.login.lockout_cleared",
        resource="UserAccount",
        resource_identifier=str(account.pk),
        context={"result": "success", "cleared_failed_attempts": cleared_attempts},
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
        raise AccountTemporarilyLockedError(account.locked_until)

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
            raise AccountTemporarilyLockedError(account.locked_until)
        raise InvalidCredentialsError

    if user.failed_login_attempts or user.locked_until:
        cleared_attempts = user.failed_login_attempts
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=["failed_login_attempts", "locked_until"])
        _audit_login_lockout_cleared(account=user, cleared_attempts=cleared_attempts)
    # U5: el historial de accesos de la ficha de la cuenta sale de la bitacora;
    # sin este asiento solo quedaban registrados los intentos fallidos.
    record_event(
        actor=user,
        action="identity.login.succeeded",
        resource="UserAccount",
        resource_identifier=str(user.pk),
        context={"result": "success"},
    )
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
        raise AuthorizationError("El actor no tiene permiso para asignar roles.")
    if actor.pk == user.pk:
        record_event(
            actor=actor,
            action="identity.role_assignment.create_denied",
            resource="UserAccount",
            resource_identifier=str(user.pk),
            context={"result": "denied", "reason": "self_escalation"},
        )
        raise AuthorizationError("Nadie puede asignarse roles a si mismo.")
    if not role.is_active:
        raise DomainError("El rol está retirado y no se puede asignar.")
    if user.status == user.AccountStatus.DISABLED:
        raise DomainError("No se pueden asignar roles a una cuenta desactivada.")

    scope = dict(scope or {})
    if scope.pop("teaching_assignments", False):
        # RA4: "usar sus asignaciones docentes vigentes". El alcance docente ya se
        # deriva dinamicamente de las asignaciones vigentes (RF-ALC-002); este
        # grant deja registrada la decision y se muestra como tal, sin copiar
        # asignaciones que mañana cambian.
        if getattr(getattr(user, "person", None), "teacher_profile", None) is None:
            raise DomainError(
                "La persona de esta cuenta no es docente: no tiene asignaciones docentes "
                "que usar como alcance."
            )
        scope["module_key"] = TEACHING_ASSIGNMENTS_SCOPE_KEY
    if not any(scope.get(field_name) for field_name in ScopeGrant.SCOPE_FIELDS):
        raise DomainError("Las asignaciones de rol requieren un alcance explicito.")

    assignment, created = RoleAssignment.objects.get_or_create(
        user=user,
        role=role,
        starts_at=starts_at or timezone.now(),
        defaults={"ends_at": ends_at},
    )
    if not created and ends_at != assignment.ends_at:
        assignment.ends_at = ends_at
        assignment.save(update_fields=["ends_at", "updated_at"])

    grant, _ = ScopeGrant.objects.get_or_create(
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
        resource_identifier=str(assignment.public_id),
        context={
            "target_user_id": user.pk,
            "role_slug": role.slug,
            "starts_at": assignment.starts_at.isoformat(),
            "ends_at": assignment.ends_at.isoformat() if assignment.ends_at else None,
            "scope": scope_grant_reference(grant),
            "result": "success",
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
        raise AuthorizationError("El actor no tiene permiso para revocar asignaciones de rol.")
    if actor.pk == assignment.user_id:
        record_event(
            actor=actor,
            action="identity.role_assignment.revoke_denied",
            resource="RoleAssignment",
            resource_identifier=str(assignment.public_id),
            context={"result": "denied", "reason": "self_escalation"},
        )
        raise AuthorizationError("Nadie puede revocar sus propios roles.")

    effective_end = ends_at or timezone.now()
    with transaction.atomic():
        locked_assignment = RoleAssignment.objects.select_for_update().get(pk=assignment.pk)
        if locked_assignment.role.permissions.filter(codename=ACCOUNT_CREATE_PERMISSION).exists():
            _ensure_account_administrator_remains(assignment=locked_assignment)
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
        raise DomainError("Los roles del sistema requieren autorizacion elevada.")
    return role


def get_account_active_dependencies(user):
    """RF-CTA-006: Retorna dependencias vigentes que quedarían sin responsable."""
    from apps.academics.models import AcademicCycle, TeachingAssignment

    if not user.person_id:
        return {"teaching_assignments": []}

    assignments = list(
        TeachingAssignment.objects.filter(
            teacher_id=user.person_id,
            academic_cycle__status=AcademicCycle.CycleStatus.ACTIVE,
            ends_on__isnull=True,
        )
        .select_related("section", "subject")
        .values("public_id", "section__name", "subject__name")
    )
    return {"teaching_assignments": assignments}


def disable_account(*, actor, user, force=False, reason=""):
    is_authorized = bool(_has_identity_permission(actor, ACCOUNT_DISABLE_PERMISSION))
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
        raise AuthorizationError("El actor no tiene permiso para deshabilitar cuentas.")
    if actor.pk == user.pk:
        record_event(
            actor=actor,
            action="identity.account.disable_denied",
            resource="UserAccount",
            resource_identifier=str(user.pk),
            context={
                "target_user_id": user.pk,
                "result": "denied",
                "reason": "self_deactivation",
            },
        )
        raise AuthorizationError("Nadie puede deshabilitar su propia cuenta.")

    deps = get_account_active_dependencies(user)
    if deps["teaching_assignments"] and not force:
        return {"warnings": deps, "disabled": False}

    with transaction.atomic():
        account = user.__class__.objects.select_for_update().get(pk=user.pk)
        if _active_account_administrators().filter(user=account).exists():
            _ensure_account_administrator_remains(user=account)
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
            reason=reason,
            context={
                "target_user_id": account.pk,
                "before": previous_state,
                "after": {
                    "status": account.status,
                    "is_active": account.is_active,
                },
                "result": "success",
                "forced_with_dependencies": bool(deps["teaching_assignments"]),
            },
        )
        return {"account": account, "disabled": True, "warnings": deps}


def _session_keys_for_user(*, user):
    """Return live server-side session keys owned by ``user`` without exposing their data."""
    user_id_str = str(user.pk)
    keys = []
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) == user_id_str:
            keys.append(session.session_key)
    return keys


def close_account_sessions(*, actor, user, current_session_key=None, administrative=False):
    """Close every active session for an account and audit the security operation."""
    is_self_service = actor and actor.pk == user.pk
    if not is_self_service and not _has_identity_permission(actor, ACCOUNT_DISABLE_PERMISSION):
        record_event(
            actor=actor,
            action="identity.session.close_denied",
            resource="UserAccount",
            resource_identifier=str(user.pk),
            context={"target_user_id": user.pk, "result": "denied", "reason": "missing_permission"},
        )
        raise AuthorizationError(
            "El actor no tiene permiso para cerrar las sesiones de esta cuenta."
        )

    session_keys = _session_keys_for_user(user=user)
    if session_keys:
        Session.objects.filter(session_key__in=session_keys).delete()

    action = "identity.session.closed_all"
    if administrative and not is_self_service:
        action = "identity.session.closed_administratively"
    record_event(
        actor=actor,
        action=action,
        resource="UserAccount",
        resource_identifier=str(user.pk),
        context={
            "target_user_id": user.pk,
            "closed_session_count": len(session_keys),
            "current_session_included": bool(current_session_key in session_keys),
            "result": "success",
        },
    )
    return len(session_keys)


def close_session_key(*, session_key, actor, target, reason):
    """Close a specific server-side session without exposing its payload."""
    if session_key:
        Session.objects.filter(session_key=session_key).delete()
    record_event(
        actor=actor,
        action="identity.session.closed",
        resource="UserAccount",
        resource_identifier=str(target.pk),
        context={"target_user_id": target.pk, "reason": reason, "result": "success"},
    )


def close_other_user_sessions(*, user, current_session_key=None):
    """Password changes preserve the current session while invalidating the rest."""
    session_keys = [key for key in _session_keys_for_user(user=user) if key != current_session_key]
    if session_keys:
        Session.objects.filter(session_key__in=session_keys).delete()
    return len(session_keys)


def record_current_session_logout(*, user):
    if getattr(user, "is_authenticated", False):
        record_event(
            actor=user,
            action="identity.session.closed_current",
            resource="UserAccount",
            resource_identifier=str(user.pk),
            context={"target_user_id": user.pk, "result": "success"},
        )


def effective_session_idle_timeout_minutes(*, user, when=None):
    """Use the widest timeout among active roles to avoid interrupting capture work."""
    when = when or timezone.now()
    timeouts = (
        RoleAssignment.objects.active_at(when)
        .filter(
            user=user,
            is_active=True,
            role__is_active=True,
        )
        .values_list("role__session_idle_timeout_minutes", flat=True)
    )
    return max(timeouts, default=settings.DEFAULT_SESSION_IDLE_TIMEOUT_MINUTES)


def refresh_session_activity(*, request, user, now=None):
    """Roll server-side session expiry after an authenticated request or fresh login."""
    if not getattr(user, "is_authenticated", False) or not hasattr(request, "session"):
        return None
    now = now or timezone.now()
    timeout_minutes = effective_session_idle_timeout_minutes(user=user, when=now)
    request.session["identity.session_last_activity_at"] = now.isoformat()
    request.session.set_expiry(timeout_minutes * 60)
    return timeout_minutes


def change_password(*, user, current_password, new_password, request=None):
    """
    RF-AUT-006: Permite al titular cambiar su contraseña exigiendo la contraseña vigente.
    Cierra las demás sesiones activas y registra el evento en bitácora sin guardar texto claro.
    """
    if not user or not getattr(user, "is_authenticated", False):
        raise AuthorizationError("Debe estar autenticado para cambiar la contraseña.")

    if not user.check_password(current_password):
        record_event(
            actor=user,
            action="identity.password.change_denied",
            resource="UserAccount",
            resource_identifier=str(user.pk),
            context={"reason": "invalid_current_password"},
        )
        raise DomainError("La contraseña actual es incorrecta.")

    validate_password(new_password, user=user)

    user.set_password(new_password)
    user.save(update_fields=["password"])

    current_session_key = getattr(getattr(request, "session", None), "session_key", None)
    close_other_user_sessions(user=user, current_session_key=current_session_key)

    if request and hasattr(request, "session") and getattr(request, "user", None) == user:
        update_session_auth_hash(request, user)

    record_event(
        actor=user,
        action="identity.password.changed",
        resource="UserAccount",
        resource_identifier=str(user.pk),
        context={"result": "success"},
    )
    return user


def _reset_token_digest(token):
    # El algoritmo queda explicito: los resumenes ya emitidos usan SHA-1 y el
    # valor por defecto de salted_hmac cambia a SHA-256 en Django 2028.
    return salted_hmac("identity.password_reset", token, algorithm="sha1").hexdigest()


@transaction.atomic
def issue_password_reset(*, actor, account):
    """RF-CTA-005: issue one opaque secret without ever handling a password."""
    if not _has_identity_permission(actor, ACCOUNT_DISABLE_PERMISSION):
        record_event(
            actor=actor,
            action="identity.password_reset.issue_denied",
            resource="UserAccount",
            resource_identifier=str(account.pk),
            context={"result": "denied"},
        )
        raise AuthorizationError("El actor no tiene permiso para administrar esta cuenta.")
    PasswordResetChallenge.objects.filter(
        account=account, used_at__isnull=True, revoked_at__isnull=True
    ).update(revoked_at=timezone.now())
    token = secrets.token_urlsafe(32)
    challenge = PasswordResetChallenge.objects.create(
        account=account,
        token_digest=_reset_token_digest(token),
        expires_at=timezone.now() + timedelta(minutes=PASSWORD_RESET_TTL_MINUTES),
    )
    record_event(
        actor=actor,
        action="identity.password_reset.issued",
        resource="UserAccount",
        resource_identifier=str(account.pk),
        context={
            "target_user_id": account.pk,
            "challenge_id": str(challenge.public_id),
            "result": "success",
        },
    )
    return challenge, token


@transaction.atomic
def consume_password_reset(*, token, new_password):
    """Consume a reset secret once and invalidate every pre-existing session."""
    challenge = (
        PasswordResetChallenge.objects.select_related("account")
        .filter(token_digest=_reset_token_digest(token))
        .first()
    )
    if challenge is None or not challenge.is_usable():
        record_event(
            actor=None,
            action="identity.password_reset.consume_denied",
            resource="PasswordResetChallenge",
            context={"result": "denied"},
        )
        raise DomainError("El enlace de restablecimiento no es valido o ya vencio.")
    account = challenge.account
    try:
        validate_password(new_password, user=account)
    except ValidationError as exc:
        raise FieldValidationError({"password": exc.messages}) from exc
    account.set_password(new_password)
    account.save(update_fields=["password"])
    close_account_sessions(actor=account, user=account)
    challenge.used_at = timezone.now()
    challenge.save(update_fields=["used_at", "updated_at"])
    record_event(
        actor=account,
        action="identity.password_reset.consumed",
        resource="UserAccount",
        resource_identifier=str(account.pk),
        context={"challenge_id": str(challenge.public_id), "result": "success"},
    )
    return account


def my_weekly_schedule(*, actor):
    """
    RF-HOR-010: the caller's own weekly schedule -- sessions they teach or
    sessions of their wards' sections, published cycles only (RF-HOR-009).

    Denied for an account that is neither a teacher nor an active guardian:
    there is no delegated-scope angle here (unlike student records), so no
    atomic permission gates this -- only the account's own identity does.
    """
    if not scopes.has_own_schedule_scope(user=actor):
        record_event(
            actor=actor,
            action="identity.my_schedule.read_denied",
            resource="ClassSession",
            resource_identifier=str(actor.pk),
            context={"result": "denied", "reason": "no_teacher_or_guardian_scope"},
        )
        raise AuthorizationError(
            "La cuenta no esta vinculada a un docente ni a un encargado activo."
        )

    queryset = scopes.my_weekly_schedule_queryset(user=actor)
    record_event(
        actor=actor,
        action="identity.my_schedule.read",
        resource="ClassSession",
        resource_identifier=str(actor.pk),
        context={"result": "success"},
    )
    return queryset


# --------------------------------------------------------------------------- #
# Presentacion de permisos efectivos y alcances (docs/ux-ui.md 1.4, MC1, RA1)
# --------------------------------------------------------------------------- #


def effective_permission_codes(*, user, when=None):
    """
    1.4: permisos atomicos efectivos de la cuenta, con codigo publico.

    Es solo presentacion: el menu y los botones se ocultan con esto, pero cada
    operacion se sigue autorizando en el backend (permiso y alcance). Replica
    las condiciones de ``UserAccount.has_atomic_permission`` para que el menu
    no ofrezca nada que esa evaluacion negaria por estado de la cuenta.
    """
    if not getattr(user, "is_authenticated", False):
        return []
    if user.is_superuser:
        return sorted(code for code, _label in ATOMIC_PERMISSIONS)
    if not user.is_active or user.status != user.AccountStatus.ACTIVE or user.is_locked():
        return []
    student = getattr(getattr(user, "person", None), "student_profile", None)
    if student is not None and student.status != student.StudentStatus.ACTIVE:
        return []
    when = when or timezone.now()
    codenames = (
        RoleAssignment.objects.active_at(when)
        .filter(is_active=True, user=user, role__is_active=True)
        .values_list("role__permissions__codename", flat=True)
        .distinct()
    )
    return sorted(
        {
            ATOMIC_PERMISSION_CODES_BY_CODENAME[codename]
            for codename in codenames
            if codename in ATOMIC_PERMISSION_CODES_BY_CODENAME
        }
    )


def _person_full_name(person):
    if person is None:
        return ""
    return f"{person.first_name} {person.last_name}".strip()


def describe_scope_grant(grant):
    """
    RA1/MC1: las dimensiones de un alcance con su ``public_id`` y una etiqueta
    que la persona reconoce ("1.º Básico A", "Matemática"), nunca ids internos.
    """
    parts = []
    if grant.institution_id:
        parts.append(
            {
                "dimension": "institution",
                "public_id": str(grant.institution.public_id),
                "label": grant.institution.name,
            }
        )
    if grant.academic_cycle_id:
        parts.append(
            {
                "dimension": "academic_cycle",
                "public_id": str(grant.academic_cycle.public_id),
                "label": grant.academic_cycle.name,
            }
        )
    if grant.grade_id:
        parts.append(
            {
                "dimension": "grade",
                "public_id": str(grant.grade.public_id),
                "label": grant.grade.presentation_label or grant.grade.name,
            }
        )
    if grant.section_id:
        parts.append(
            {
                "dimension": "section",
                "public_id": str(grant.section.public_id),
                "label": str(grant.section),
            }
        )
    if grant.subject_id:
        parts.append(
            {
                "dimension": "subject",
                "public_id": str(grant.subject.public_id),
                "label": grant.subject.name,
            }
        )
    if grant.teaching_assignment_id:
        assignment = grant.teaching_assignment
        parts.append(
            {
                "dimension": "teaching_assignment",
                "public_id": str(assignment.public_id),
                "label": f"{assignment.subject.name} · {assignment.section}",
            }
        )
    if grant.student_id:
        student = grant.student
        parts.append(
            {
                "dimension": "student",
                "public_id": str(student.public_id),
                "label": " · ".join(
                    part
                    for part in (_person_full_name(student.person), student.student_code)
                    if part
                ),
            }
        )
    if grant.module_key:
        parts.append(
            {
                "dimension": "module",
                "public_id": None,
                "value": grant.module_key,
                "label": SCOPE_MODULE_LABELS.get(grant.module_key, grant.module_key),
            }
        )
    return parts


def scope_grant_reference(grant):
    """Referencia compacta del alcance para la bitacora (``public_id`` o modulo)."""
    return {
        part["dimension"]: part.get("public_id") or part.get("value")
        for part in describe_scope_grant(grant)
    }


def assignment_status(assignment, *, when=None):
    """
    Estado de vigencia de una asignacion de rol, para mostrar y para RA5.

    ``revoked`` y ``expired`` no se distinguen en el modelo (revocar adelanta
    ``ends_at``); los dos se muestran como finalizada y la bitacora conserva cual
    de las dos fue.
    """
    when = when or timezone.now()
    if not assignment.is_active:
        return "ended"
    if assignment.starts_at > when:
        return "scheduled"
    if assignment.ends_at is not None and assignment.ends_at < when:
        return "ended"
    if assignment.ends_at is not None and assignment.ends_at <= when + timedelta(
        days=EXPIRING_ASSIGNMENT_DAYS
    ):
        return "expiring"
    return "active"


def account_sessions(*, user, current_session_key=None):
    """
    MC1/U5: sesiones vivas de la cuenta, sin exponer su clave ni su contenido.
    Solo se devuelve cuando fue la ultima actividad, cuando vence y si es la
    sesion desde la que se consulta.
    """
    user_id = str(user.pk)
    sessions = []
    for session in Session.objects.filter(expire_date__gte=timezone.now()).order_by("-expire_date"):
        data = session.get_decoded()
        if str(data.get("_auth_user_id")) != user_id:
            continue
        sessions.append(
            {
                "last_activity_at": data.get("identity.session_last_activity_at"),
                "expires_at": session.expire_date,
                "is_current": bool(current_session_key)
                and session.session_key == current_session_key,
            }
        )
    return sessions


# --------------------------------------------------------------------------- #
# Administracion de cuentas (U1, U6, U7; ADR-0011 D8)
# --------------------------------------------------------------------------- #


def suggest_username(*, person):
    """
    U1: usuario sugerido ``nombre.apellido`` (primer nombre y primer apellido,
    sin tildes ni espacios). Si ya existe se numera. Es una sugerencia: quien da
    el acceso puede cambiarla antes de crear la cuenta.
    """
    first = slugify((person.first_name or "").split(" ")[0]).replace("-", "")
    last = slugify((person.last_name or "").split(" ")[0]).replace("-", "")
    base = ".".join(part for part in (first, last) if part)[:140] or "usuario"
    user_model = get_user_model()
    candidate = base
    suffix = 2
    while user_model.objects.filter(username__iexact=candidate).exists():
        candidate = f"{base}{suffix}"
        suffix += 1
    return candidate


def _deny_account_operation(*, actor, account, action, reason):
    record_event(
        actor=actor,
        action=f"identity.account.{action}_denied",
        resource="UserAccount",
        resource_identifier=str(account.pk),
        context={"target_user_id": account.pk, "result": "denied", "reason": reason},
    )


def update_account(*, actor, account, username=None, email=None):
    """U7: corrige usuario o correo de otra cuenta. Requiere ``account.create``."""
    if not _has_identity_permission(actor, ACCOUNT_CREATE_PERMISSION):
        _deny_account_operation(
            actor=actor, account=account, action="update", reason="missing_permission"
        )
        raise AuthorizationError("El actor no tiene permiso para editar cuentas.")

    user_model = get_user_model()
    with transaction.atomic():
        locked = user_model.objects.select_for_update().get(pk=account.pk)
        changes = {}
        if username is not None and username != locked.username:
            if user_model.objects.filter(username__iexact=username).exclude(pk=locked.pk).exists():
                raise DomainError("Ya existe una cuenta con este usuario.")
            changes["username"] = {"before": locked.username, "after": username}
            locked.username = username
        if email is not None and email != locked.email:
            changes["email"] = {"before": locked.email, "after": email}
            locked.email = email
        if not changes:
            return locked
        locked.save(update_fields=list(changes))
        record_event(
            actor=actor,
            action="identity.account.updated",
            resource="UserAccount",
            resource_identifier=str(locked.pk),
            context={"target_user_id": locked.pk, "result": "success"},
            changes=changes,
        )
    return locked


def reactivate_account(*, actor, account, reason):
    """
    D8 / RF-CTA-008: una cuenta desactivada vuelve a ``pending`` con un codigo de
    activacion nuevo. La persona define otra contraseña al activarla; la anterior
    queda inutilizable. Las asignaciones de rol no se tocan: las revocadas siguen
    revocadas y ninguna vuelve sola.
    """
    if not _has_identity_permission(actor, ACCOUNT_ACTIVATE_PERMISSION):
        _deny_account_operation(
            actor=actor, account=account, action="reactivate", reason="missing_permission"
        )
        raise AuthorizationError("El actor no tiene permiso para reactivar cuentas.")
    if actor.pk == account.pk:
        _deny_account_operation(
            actor=actor, account=account, action="reactivate", reason="self_reactivation"
        )
        raise AuthorizationError("Nadie puede reactivar su propia cuenta.")
    if not (reason or "").strip():
        raise DomainError("Indique el motivo de la reactivación.")

    with transaction.atomic():
        locked = account.__class__.objects.select_for_update().get(pk=account.pk)
        if locked.status != locked.AccountStatus.DISABLED:
            raise DomainError("Solo se puede reactivar una cuenta desactivada.")
        before = {"status": locked.status, "is_active": locked.is_active}
        locked.status = locked.AccountStatus.PENDING
        locked.is_active = False
        locked.failed_login_attempts = 0
        locked.locked_until = None
        locked.set_unusable_password()
        locked.save(
            update_fields=[
                "status",
                "is_active",
                "failed_login_attempts",
                "locked_until",
                "password",
            ]
        )
        record_event(
            actor=actor,
            action="identity.account.reactivated",
            resource="UserAccount",
            resource_identifier=str(locked.pk),
            reason=reason.strip(),
            context={
                "target_user_id": locked.pk,
                "before": before,
                "after": {"status": locked.status, "is_active": locked.is_active},
                "roles_restored": False,
                "result": "success",
            },
        )
        challenge, code = _issue_activation_challenge(
            actor=actor, account=locked, reason="reactivation"
        )
    return locked, challenge, code


def unlock_account(*, actor, account, reason):
    """
    D8 / RF-CTA-008: levanta el bloqueo temporal por intentos fallidos y reinicia
    el contador, sin esperar a que venza. No cambia el estado ni la contraseña.
    """
    if not _has_identity_permission(actor, ACCOUNT_ACTIVATE_PERMISSION):
        _deny_account_operation(
            actor=actor, account=account, action="unlock", reason="missing_permission"
        )
        raise AuthorizationError("El actor no tiene permiso para desbloquear cuentas.")
    if actor.pk == account.pk:
        _deny_account_operation(actor=actor, account=account, action="unlock", reason="self_unlock")
        raise AuthorizationError("Nadie puede desbloquear su propia cuenta.")
    if not (reason or "").strip():
        raise DomainError("Indique el motivo del desbloqueo.")

    with transaction.atomic():
        locked = account.__class__.objects.select_for_update().get(pk=account.pk)
        if not locked.is_locked() and not locked.failed_login_attempts:
            raise DomainError("La cuenta no está bloqueada.")
        before = {
            "failed_login_attempts": locked.failed_login_attempts,
            "locked_until": locked.locked_until.isoformat() if locked.locked_until else None,
        }
        locked.failed_login_attempts = 0
        locked.locked_until = None
        locked.save(update_fields=["failed_login_attempts", "locked_until"])
        record_event(
            actor=actor,
            action="identity.account.unlocked",
            resource="UserAccount",
            resource_identifier=str(locked.pk),
            reason=reason.strip(),
            context={
                "target_user_id": locked.pk,
                "before": before,
                "after": {"failed_login_attempts": 0, "locked_until": None},
                "result": "success",
            },
        )
    return locked


# --------------------------------------------------------------------------- #
# Retiro seguro de roles (RO6)
# --------------------------------------------------------------------------- #


def deactivate_role(*, actor, role, reason):
    """
    RO6: un rol que ya no se usa se retira (``is_active=False``), nunca se borra:
    su historia de asignaciones y la bitacora siguen apuntandolo. Solo se retira
    si nadie lo tiene vigente ni programado; si no, quien lo retira debe revocar
    antes esas asignaciones, para que nadie pierda acceso sin darse cuenta.
    """
    if not _can_manage_roles(actor):
        _audit_role_denied(actor=actor, action="deactivate", role=role)
        raise AuthorizationError("El actor no tiene permiso para retirar roles.")
    if role.is_system:
        _audit_role_denied(actor=actor, action="deactivate", role=role, reason="system_role")
        raise DomainError("Los roles del sistema no se pueden retirar.")
    if not (reason or "").strip():
        raise DomainError("Indique el motivo del retiro del rol.")

    now = timezone.now()
    with transaction.atomic():
        locked = Role.objects.select_for_update().get(pk=role.pk)
        if not locked.is_active:
            raise DomainError("El rol ya está retirado.")
        pending = (
            RoleAssignment.objects.filter(role=locked, is_active=True)
            .filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=now))
            .count()
        )
        if pending:
            raise DomainError(
                f"El rol tiene {pending} asignación(es) vigente(s) o programada(s). "
                "Revóquelas antes de retirarlo."
            )
        locked.is_active = False
        locked.save(update_fields=["is_active", "updated_at"])
        record_event(
            actor=actor,
            action="identity.role.deactivated",
            resource="Role",
            resource_identifier=str(locked.public_id),
            reason=reason.strip(),
            context={"result": "success", "role_slug": locked.slug},
        )
    return locked


def reactivate_role(*, actor, role, reason):
    """RO6: un rol retirado puede volver a ofrecerse. Las asignaciones no vuelven."""
    if not _can_manage_roles(actor):
        _audit_role_denied(actor=actor, action="reactivate", role=role)
        raise AuthorizationError("El actor no tiene permiso para reactivar roles.")
    if not (reason or "").strip():
        raise DomainError("Indique el motivo de la reactivación del rol.")
    with transaction.atomic():
        locked = Role.objects.select_for_update().get(pk=role.pk)
        if locked.is_active:
            raise DomainError("El rol ya está activo.")
        locked.is_active = True
        locked.save(update_fields=["is_active", "updated_at"])
        record_event(
            actor=actor,
            action="identity.role.reactivated",
            resource="Role",
            resource_identifier=str(locked.public_id),
            reason=reason.strip(),
            context={"result": "success", "role_slug": locked.slug},
        )
    return locked


def ensure_identity_permission(*, actor, codename, denial_action, resource=""):
    """Lecturas administrativas de identidad: permiso sobre el modulo o 403 auditado."""
    if _has_identity_permission(actor, codename):
        return
    record_event(
        actor=actor,
        action=denial_action,
        resource=resource,
        context={"result": "denied", "reason": "missing_permission", "permission": codename},
    )
    raise AuthorizationError("El actor no tiene permiso para esta consulta de identidad.")


def password_policy_rules():
    """
    MC2: las reglas reales de contraseña, leidas de los validadores que aplica
    ``validate_password``, para que las pantallas no prometan una regla distinta.
    """
    from django.contrib.auth.password_validation import password_validators_help_texts

    return password_validators_help_texts()
