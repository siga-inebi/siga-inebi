from rest_framework.permissions import BasePermission

from apps.audit.services import record_event


class ScopedAtomicPermission(BasePermission):
    message = "La operacion requiere permiso y alcance validos."

    def has_permission(self, request, view):
        codename = getattr(view, "permission_codename", "")
        scope = getattr(view, "permission_scope", None)
        if not codename or not scope:
            self._audit_denied(request, view, codename, scope, "authorization_not_declared")
            return False
        if request.user.is_superuser:
            return True
        allowed = request.user.has_scoped_permission(codename, scope=scope)
        if not allowed:
            self._audit_denied(request, view, codename, scope, "missing_permission_or_scope")
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
