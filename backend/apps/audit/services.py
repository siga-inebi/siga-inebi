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


def record_event(*, actor, action, resource, resource_identifier="", context=None, ip_address=None):
    merged_context = {}
    merged_context.update(get_audit_context())
    if context:
        merged_context.update(context)

    return AuditEvent.objects.create(
        actor=actor,
        actor_label=getattr(actor, "username", "") if actor else "",
        action=action,
        resource=resource,
        resource_identifier=resource_identifier,
        ip_address=ip_address or merged_context.get("ip_address") or None,
        context=sanitize_context(merged_context),
    )


def list_audit_events(*, actor_id=None, resource=None, action=None, date_from=None, date_to=None):
    """
    RF-BIT-006: the filterable read of the audit trail. Callers must already
    have verified the actor holds the audit-read permission before calling
    this -- it applies the filters, it does not authorize the read.
    """
    queryset = AuditEvent.objects.all()
    if actor_id is not None:
        queryset = queryset.filter(actor_id=actor_id)
    if resource:
        queryset = queryset.filter(resource=resource)
    if action:
        queryset = queryset.filter(action=action)
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
    return queryset


def record_audit_export(*, actor, date_from, date_to, count):
    """RF-BIT-006: exporting audit entries is itself an audited operation."""
    return record_event(
        actor=actor,
        action="audit.export.created",
        resource="AuditEvent",
        context={
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
            "count": count,
        },
    )
