from django.contrib import admin

from apps.academics.models import (
    AcademicCycle,
    Campus,
    CurriculumPlan,
    Grade,
    GradeOffering,
    Institution,
    Level,
    LevelSubject,
    Section,
    Shift,
    Subject,
    TeachingAssignment,
)

admin.site.register(Institution)
admin.site.register(Campus)
admin.site.register(AcademicCycle)
admin.site.register(Shift)
admin.site.register(Level)
admin.site.register(Grade)
admin.site.register(GradeOffering)
admin.site.register(Section)
admin.site.register(Subject)
admin.site.register(LevelSubject)
admin.site.register(CurriculumPlan)
admin.site.register(TeachingAssignment)
