from django.contrib import admin

from apps.audit.models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "resource", "resource_identifier", "actor_label")
    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
        "actor",
        "actor_label",
        "action",
        "resource",
        "resource_identifier",
        "ip_address",
        "context",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
