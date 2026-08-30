from django.urls import include, path

from apps.evaluation.api.views import (
    CurrentAverageView,
    CycleEvaluationConfigView,
    EvaluationGlobalConfigView,
    FinalSubjectGradeView,
)

from .views import (
    AcademicCycleActivateView,
    AcademicCycleCloneView,
    AcademicCycleCloseView,
    AcademicCycleDefaultsView,
    AcademicCycleListCreateView,
    CampusDetailView,
    CampusListCreateView,
    CampusNextCodeView,
    CampusShiftListCreateView,
    ClassScheduleBlockDetailView,
    ClassSchedulePublicationView,
    ClassSessionDetailView,
    CurriculumPlanDetailView,
    CurriculumPlanListCreateView,
    GradeDetailView,
    HistoricalAcademicCycleDetailView,
    LevelDetailView,
    LevelGradeListCreateView,
    LevelGradeNextCodeView,
    LevelListCreateView,
    LevelNextCodeView,
    LevelSubjectDetailView,
    LevelSubjectListCreateView,
    SectionClassSessionListCreateView,
    SectionDetailView,
    SectionListCreateView,
    ShiftClassScheduleBlockListCreateView,
    ShiftDetailView,
    SubjectDetailView,
    SubjectListCreateView,
    TeachingAssignmentHistoryView,
    TeachingAssignmentListCreateView,
    TeachingAssignmentReassignView,
)

urlpatterns = [
    path("cycles/", AcademicCycleListCreateView.as_view(), name="academic-cycle-list-create"),
    # Antes de "cycles/<uuid:public_id>/": el convertidor uuid no captura texto,
    # pero el orden lo deja explicito para quien lea las rutas.
    path(
        "cycles/defaults/",
        AcademicCycleDefaultsView.as_view(),
        name="academic-cycle-defaults",
    ),
    path(
        "cycles/<uuid:public_id>/",
        HistoricalAcademicCycleDetailView.as_view(),
        name="academic-cycle-historical-detail",
    ),
    path(
        "cycles/<uuid:public_id>/activate/",
        AcademicCycleActivateView.as_view(),
        name="academic-cycle-activate",
    ),
    path(
        "cycles/<uuid:public_id>/close/",
        AcademicCycleCloseView.as_view(),
        name="academic-cycle-close",
    ),
    path(
        "cycles/<uuid:public_id>/schedule-publication/",
        ClassSchedulePublicationView.as_view(),
        name="class-schedule-publication",
    ),
    path(
        "cycles/<uuid:cycle_public_id>/evaluation-units/",
        include("apps.evaluation.api.urls"),
    ),
    path(
        "evaluation-config/",
        EvaluationGlobalConfigView.as_view(),
        name="evaluation-global-config",
    ),
    path(
        "cycles/<uuid:cycle_public_id>/evaluation-config/",
        CycleEvaluationConfigView.as_view(),
        name="cycle-evaluation-config",
    ),
    path(
        "cycles/<uuid:cycle_public_id>/enrolments/<uuid:enrolment_id>/subjects/<uuid:subject_id>/current-average/",
        CurrentAverageView.as_view(),
        name="grade-current-average",
    ),
    path(
        "cycles/<uuid:cycle_public_id>/enrolments/<uuid:enrolment_id>/subjects/<uuid:subject_id>/final-grade/",
        FinalSubjectGradeView.as_view(),
        name="grade-final-subject-grade",
    ),
    path(
        "cycles/<uuid:public_id>/clone/",
        AcademicCycleCloneView.as_view(),
        name="academic-cycle-clone",
    ),
    # institutional structure: sedes y jornadas
    path("campuses/", CampusListCreateView.as_view(), name="campus-list-create"),
    path("campuses/next-code/", CampusNextCodeView.as_view(), name="campus-next-code"),
    path("campuses/<uuid:public_id>/", CampusDetailView.as_view(), name="campus-detail"),
    path(
        "campuses/<uuid:public_id>/shifts/",
        CampusShiftListCreateView.as_view(),
        name="campus-shift-list-create",
    ),
    path("shifts/<uuid:public_id>/", ShiftDetailView.as_view(), name="shift-detail"),
    path(
        "shifts/<uuid:public_id>/schedule-blocks/",
        ShiftClassScheduleBlockListCreateView.as_view(),
        name="shift-schedule-block-list-create",
    ),
    path(
        "schedule-blocks/<uuid:public_id>/",
        ClassScheduleBlockDetailView.as_view(),
        name="schedule-block-detail",
    ),
    # academic structure: niveles, grados y cursos
    path("levels/", LevelListCreateView.as_view(), name="level-list-create"),
    path("levels/next-code/", LevelNextCodeView.as_view(), name="level-next-code"),
    path("levels/<uuid:public_id>/", LevelDetailView.as_view(), name="level-detail"),
    path(
        "levels/<uuid:public_id>/grades/",
        LevelGradeListCreateView.as_view(),
        name="level-grade-list-create",
    ),
    path(
        "levels/<uuid:public_id>/grades/next-code/",
        LevelGradeNextCodeView.as_view(),
        name="level-grade-next-code",
    ),
    path("grades/<uuid:public_id>/", GradeDetailView.as_view(), name="grade-detail"),
    path(
        "levels/<uuid:public_id>/subjects/",
        LevelSubjectListCreateView.as_view(),
        name="level-subject-list-create",
    ),
    path(
        "levels/<uuid:public_id>/subjects/<uuid:subject_public_id>/",
        LevelSubjectDetailView.as_view(),
        name="level-subject-detail",
    ),
    path("subjects/", SubjectListCreateView.as_view(), name="subject-list-create"),
    path("subjects/<uuid:public_id>/", SubjectDetailView.as_view(), name="subject-detail"),
    path("sections/", SectionListCreateView.as_view(), name="section-list-create"),
    path("sections/<uuid:public_id>/", SectionDetailView.as_view(), name="section-detail"),
    path(
        "sections/<uuid:public_id>/class-sessions/",
        SectionClassSessionListCreateView.as_view(),
        name="section-class-session-list-create",
    ),
    path(
        "class-sessions/<uuid:public_id>/",
        ClassSessionDetailView.as_view(),
        name="class-session-detail",
    ),
    path(
        "curriculum-plans/",
        CurriculumPlanListCreateView.as_view(),
        name="curriculum-plan-list-create",
    ),
    path(
        "curriculum-plans/<uuid:public_id>/",
        CurriculumPlanDetailView.as_view(),
        name="curriculum-plan-detail",
    ),
    path(
        "teaching-assignments/",
        TeachingAssignmentListCreateView.as_view(),
        name="teaching-assignment-list-create",
    ),
    path(
        "teaching-assignments/history/",
        TeachingAssignmentHistoryView.as_view(),
        name="teaching-assignment-history",
    ),
    path(
        "teaching-assignments/<uuid:public_id>/reassignments/",
        TeachingAssignmentReassignView.as_view(),
        name="teaching-assignment-reassign",
    ),
]
