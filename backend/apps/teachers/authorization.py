"""Authorization policy for teacher profile deactivation (#632 T3)."""

from apps.audit.services import record_event
from apps.common.exceptions import AuthorizationError

TEACHER_DEACTIVATE_PERMISSION = "teacher_deactivate"
TEACHERS_SCOPE = {"module_key": "teachers"}


def may_deactivate_teacher(actor):
    return bool(
        actor
        and actor.is_authenticated
        and actor.is_active
        and (
            actor.is_superuser
            or actor.has_scoped_permission(TEACHER_DEACTIVATE_PERMISSION, scope=TEACHERS_SCOPE)
        )
    )


def require_teacher_deactivation(*, actor, teacher):
    if may_deactivate_teacher(actor):
        return
    record_event(
        actor=actor if actor and actor.is_authenticated else None,
        action="identity.authorization.denied",
        resource="Teacher",
        resource_identifier=str(teacher.pk),
        context={
            "permission": TEACHER_DEACTIVATE_PERMISSION,
            "scope": TEACHERS_SCOPE,
            "reason": "missing_permission_or_scope",
            "result": "denied",
        },
    )
    raise AuthorizationError("Se requiere permiso para desactivar docentes con alcance teachers.")
