from django.contrib import admin

from apps.evaluation.models import EvaluationUnit


@admin.register(EvaluationUnit)
class EvaluationUnitAdmin(admin.ModelAdmin):
    list_display = ["name", "academic_cycle", "number", "starts_on", "ends_on", "status"]
    list_filter = ["academic_cycle", "status"]
    search_fields = ["name"]
    readonly_fields = ["public_id", "created_at", "updated_at"]
    fieldsets = (
        (
            "Basic Information",
            {"fields": ("academic_cycle", "number", "name", "status")},
        ),
        ("Dates", {"fields": ("starts_on", "ends_on")}),
        ("Metadata", {"fields": ("public_id", "created_at", "updated_at", "is_active")}),
    )
