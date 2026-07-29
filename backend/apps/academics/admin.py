from django.contrib import admin

from apps.academics.models import (
    AcademicCycle,
    CurriculumPlan,
    Grade,
    Institution,
    Section,
    Shift,
    Subject,
    TeachingAssignment,
)

admin.site.register(Institution)
admin.site.register(AcademicCycle)
admin.site.register(Shift)
admin.site.register(Grade)
admin.site.register(Section)
admin.site.register(Subject)
admin.site.register(CurriculumPlan)
admin.site.register(TeachingAssignment)
