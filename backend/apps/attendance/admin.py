from django.contrib import admin

from apps.attendance.models import (
    AttendanceAlert,
    AttendanceEvent,
    ControlPoint,
    JornadaParameters,
)


@admin.register(JornadaParameters)
class JornadaParametersAdmin(admin.ModelAdmin):
    list_display = ["shift", "academic_cycle", "effective_from", "entry_limit_time", "closing_time"]
    list_filter = ["shift", "academic_cycle"]


@admin.register(ControlPoint)
class ControlPointAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "campus", "is_active"]
    list_filter = ["campus"]


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
        "captured_at",
    ]
    list_filter = ["shift", "movement_type", "origin"]
    date_hierarchy = "event_date"


@admin.register(AttendanceAlert)
class AttendanceAlertAdmin(admin.ModelAdmin):
    list_display = ["student", "shift", "event_date", "alert_type", "created_at"]
    list_filter = ["shift", "alert_type"]
    date_hierarchy = "event_date"
