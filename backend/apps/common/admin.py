from django.contrib import admin

from apps.common.models import TaskRun


@admin.register(TaskRun)
class TaskRunAdmin(admin.ModelAdmin):
    """Read-only: a run is history written by whoever executed the task."""

    list_display = ("name", "status", "started_at", "finished_at", "duration_ms", "host")
    list_filter = ("name", "status")
    search_fields = ("name", "error_type", "error_message")
    readonly_fields = tuple(field.name for field in TaskRun._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
