from django.contrib import admin

from apps.attendance.models import (
    AttendanceAlert,
    AttendanceEvent,
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
    list_display = ["name", "code", "campus", "is_active"]
    list_filter = ["campus"]


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

    list_display = ["student", "status", "issued_at", "is_active"]
    list_filter = ["status"]
    date_hierarchy = "issued_at"
