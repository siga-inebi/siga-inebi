from django.contrib import admin

from apps.reporting.models import AbsenceThresholdParameters, Alert


@admin.register(AbsenceThresholdParameters)
class AbsenceThresholdParametersAdmin(admin.ModelAdmin):
    list_display = ["shift", "academic_cycle", "effective_from", "max_absences", "lookback_days"]
    list_filter = ["shift", "academic_cycle"]


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ["student", "shift", "event_date", "alert_type", "is_active", "acknowledged_at"]
    list_filter = ["shift", "alert_type", "is_active"]
    date_hierarchy = "event_date"
