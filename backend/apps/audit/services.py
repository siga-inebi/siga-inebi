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


def record_sensitive_read(*, actor, action, resource, resource_identifier, student):
    """
    Audits a read that reveals sensitive/confidential data about one
    identified student (RF-BIT-003). Only call this when the request
    unambiguously names a single student -- never for aggregate or
    unscoped queries, which must not appear in the audit trail
    (docs/requirements/openspec/auditoria-bitacora.md).
    """
    return record_event(
        actor=actor,
        action=action,
        resource=resource,
        resource_identifier=resource_identifier,
        context={"student_id": student.pk, "result": "success"},
    )
