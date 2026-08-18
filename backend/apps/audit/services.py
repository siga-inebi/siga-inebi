from collections.abc import Mapping

from apps.audit.middleware import get_audit_context
from apps.audit.models import AuditEvent

SENSITIVE_CONTEXT_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "private_key",
    "credential",
    "credentials",
    "cookie",
    "cookies",
}


def sanitize_context(value):
    if isinstance(value, Mapping):
        sanitized = {}
        for key, nested_value in value.items():
            if str(key).lower() in SENSITIVE_CONTEXT_KEYS:
                continue
            sanitized[key] = sanitize_context(nested_value)
        return sanitized
    if isinstance(value, list):
        return [sanitize_context(item) for item in value]
    return value


def record_event(
    *,
    actor,
    action,
    resource,
    resource_identifier="",
    context=None,
    ip_address=None,
    reason="",
    changes=None,
):
    """
    ``reason`` and ``changes`` are RF-BIT-002's "motivo declarado" and "valor
    anterior y el nuevo" -- optional, so every existing call keeps behaving
    exactly as before. Both land inside ``context`` (no new columns): that's
    already where every other unstructured fact about an event lives.
    """
    merged_context = {}
    merged_context.update(get_audit_context())
    if context:
        merged_context.update(context)
    if reason:
        merged_context["reason"] = reason
    if changes:
        merged_context["changes"] = changes

    return AuditEvent.objects.create(
        actor=actor,
        actor_label=getattr(actor, "username", "") if actor else "",
        action=action,
        resource=resource,
        resource_identifier=resource_identifier,
        ip_address=ip_address or merged_context.get("ip_address") or None,
        context=sanitize_context(merged_context),
    )


def diff_fields(instance, **candidates):
    """
    Before/after map for ``record_event(changes=...)``. Same ``None`` means
    "not supplied" convention every domain's ``_changed``-style helper
    already uses -- call this *before* mutating ``instance``.
    """
    return {
        name: {"before": getattr(instance, name), "after": new_value}
        for name, new_value in candidates.items()
        if new_value is not None
    }
