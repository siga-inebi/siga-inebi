"""Authorization policy for guardian profile deactivation (#632 G3)."""

from apps.audit.services import record_event
from apps.common.exceptions import AuthorizationError

GUARDIAN_DEACTIVATE_PERMISSION = "guardian_deactivate"
GUARDIANS_SCOPE = {"module_key": "students"}


def may_deactivate_guardian(actor):
    return bool(
        actor
        and actor.is_authenticated
        and actor.is_active
        and (
            actor.is_superuser
            or actor.has_scoped_permission(GUARDIAN_DEACTIVATE_PERMISSION, scope=GUARDIANS_SCOPE)
        )
    )


def require_guardian_deactivation(*, actor, guardian):
    if may_deactivate_guardian(actor):
        return
    record_event(
        actor=actor if actor and actor.is_authenticated else None,
        action="identity.authorization.denied",
        resource="Guardian",
        resource_identifier=str(guardian.pk),
        context={
            "permission": GUARDIAN_DEACTIVATE_PERMISSION,
            "scope": GUARDIANS_SCOPE,
            "reason": "missing_permission_or_scope",
            "result": "denied",
        },
    )
    raise AuthorizationError("Se requiere permiso para desactivar encargados con alcance students.")
