from django.contrib import admin

from apps.attendance.models import AttendanceEvent, JornadaParameters


@admin.register(JornadaParameters)
class JornadaParametersAdmin(admin.ModelAdmin):
    list_display = ["shift", "academic_cycle", "effective_from", "entry_limit_time", "closing_time"]
    list_filter = ["shift", "academic_cycle"]


@admin.register(AttendanceEvent)
class AttendanceEventAdmin(admin.ModelAdmin):
    list_display = ["student", "shift", "event_date", "movement_type", "origin", "captured_at"]
    list_filter = ["shift", "movement_type", "origin"]
    date_hierarchy = "event_date"
