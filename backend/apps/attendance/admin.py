from django.contrib import admin

from apps.attendance import services
from apps.attendance.models import (
    AttendanceAlert,
    AttendanceEvent,
    CaptureBatch,
    ControlPoint,
    JornadaParameters,
    ManualRegistrationReason,
    StudentCredential,
)


@admin.register(JornadaParameters)
class JornadaParametersAdmin(admin.ModelAdmin):
    list_display = ["shift", "academic_cycle", "effective_from", "entry_limit_time", "closing_time"]
    list_filter = ["shift", "academic_cycle"]


@admin.register(ControlPoint)
class ControlPointAdmin(admin.ModelAdmin):
    """
    RF-ASI-005: editing ``allows_entry``/``allows_exit`` on an existing point
    goes through ``configure_control_point_movement_types`` so the change is
    audited with the responsible user, instead of a bare model save.
    """

    list_display = ["name", "code", "campus", "allows_entry", "allows_exit", "is_active"]
    list_filter = ["campus"]

    def save_model(self, request, obj, form, change):
        if change and {"allows_entry", "allows_exit"} & set(form.changed_data):
            services.configure_control_point_movement_types(
                control_point=obj,
                allows_entry=obj.allows_entry,
                allows_exit=obj.allows_exit,
                actor=request.user,
            )
            return
        super().save_model(request, obj, form, change)


@admin.register(ManualRegistrationReason)
class ManualRegistrationReasonAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_active"]


@admin.register(AttendanceEvent)
class AttendanceEventAdmin(admin.ModelAdmin):
    list_display = [
        "student",
        "shift",
        "event_date",
        "movement_type",
        "origin",
        "control_point",
        "operator",
        "manual_reason",
        "captured_at",
    ]
    list_filter = ["shift", "movement_type", "origin"]
    date_hierarchy = "event_date"


@admin.register(CaptureBatch)
class CaptureBatchAdmin(admin.ModelAdmin):
    """Support surface only: open/confirm go through the API, not here."""

    list_display = ["operator", "status", "confirmed_at", "created_at"]
    list_filter = ["status"]
    date_hierarchy = "created_at"


@admin.register(AttendanceAlert)
class AttendanceAlertAdmin(admin.ModelAdmin):
    list_display = ["student", "shift", "event_date", "alert_type", "created_at"]
    list_filter = ["shift", "alert_type"]
    date_hierarchy = "event_date"


@admin.register(StudentCredential)
class StudentCredentialAdmin(admin.ModelAdmin):
    """
    ``opaque_identifier`` is intentionally absent from every column and search
    field: the admin is a support surface, and a searchable list of live tokens
    would turn it into a place to harvest usable passes.
    """

    list_display = ["student", "status", "issued_at", "revoked_by", "is_active"]
    list_filter = ["status"]
    date_hierarchy = "issued_at"
