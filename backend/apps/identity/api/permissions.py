from rest_framework.permissions import BasePermission

from apps.audit.services import record_event


class ScopedAtomicPermission(BasePermission):
    """
    Exige un permiso atomico con alcance. La vista declara ``permission_codename``
    (uno) o ``permission_codenames`` (cualquiera de varios) y ``permission_scope``.
    Sin declaracion se deniega: denegacion por defecto (RF-PER-004).
    """

    message = "La operación requiere permiso y alcance válidos."

    def has_permission(self, request, view):
        codenames = tuple(getattr(view, "permission_codenames", ()) or ())
        single = getattr(view, "permission_codename", "")
        if single:
            codenames = (single, *codenames)
        scope = getattr(view, "permission_scope", None)
        if not codenames or not scope:
            self._audit_denied(
                request, view, ",".join(codenames), scope, "authorization_not_declared"
            )
            return False
        if request.user.is_superuser:
            return True
        allowed = any(
            request.user.has_scoped_permission(codename, scope=scope) for codename in codenames
        )
        if not allowed:
            self._audit_denied(
                request, view, ",".join(codenames), scope, "missing_permission_or_scope"
            )
        return allowed

    def _audit_denied(self, request, view, codename, scope, reason):
        actor = request.user if getattr(request.user, "is_authenticated", False) else None
        record_event(
            actor=actor,
            action="identity.authorization.denied",
            resource=view.__class__.__name__,
            context={
                "result": "denied",
                "reason": reason,
                "permission": codename,
                "scope": scope or {},
                "method": request.method,
            },
        )
