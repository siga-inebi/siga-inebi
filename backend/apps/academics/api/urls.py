from django.urls import path

from .views import (
    AcademicCycleCloseView,
    AcademicCycleDetailView,
    AcademicCycleListCreateView,
    AcademicCycleOpenView,
    CampusDetailView,
    CampusListCreateView,
    CampusShiftListCreateView,
    CycleOfferingListCreateView,
    GradeDetailView,
    GradeOfferingDetailView,
    LevelDetailView,
    LevelGradeListCreateView,
    LevelListCreateView,
    LevelSubjectDetailView,
    LevelSubjectListCreateView,
    OfferingSectionListCreateView,
    SectionDetailView,
    ShiftDetailView,
    SubjectDetailView,
    SubjectListCreateView,
)

urlpatterns = [
    # institutional structure: sedes y jornadas
    path("campuses/", CampusListCreateView.as_view(), name="campus-list-create"),
    path("campuses/<uuid:public_id>/", CampusDetailView.as_view(), name="campus-detail"),
    path(
        "campuses/<uuid:public_id>/shifts/",
        CampusShiftListCreateView.as_view(),
        name="campus-shift-list-create",
    ),
    path("shifts/<uuid:public_id>/", ShiftDetailView.as_view(), name="shift-detail"),
    # academic structure: niveles, grados y cursos
    path("levels/", LevelListCreateView.as_view(), name="level-list-create"),
    path("levels/<uuid:public_id>/", LevelDetailView.as_view(), name="level-detail"),
    path(
        "levels/<uuid:public_id>/grades/",
        LevelGradeListCreateView.as_view(),
        name="level-grade-list-create",
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
    # cycles and the offering they publish
    path("cycles/", AcademicCycleListCreateView.as_view(), name="cycle-list-create"),
    path("cycles/<uuid:public_id>/", AcademicCycleDetailView.as_view(), name="cycle-detail"),
    path("cycles/<uuid:public_id>/open/", AcademicCycleOpenView.as_view(), name="cycle-open"),
    path("cycles/<uuid:public_id>/close/", AcademicCycleCloseView.as_view(), name="cycle-close"),
    path(
        "cycles/<uuid:cycle_public_id>/offerings/",
        CycleOfferingListCreateView.as_view(),
        name="cycle-offering-list-create",
    ),
    path(
        "offerings/<uuid:public_id>/",
        GradeOfferingDetailView.as_view(),
        name="offering-detail",
    ),
    path(
        "offerings/<uuid:public_id>/sections/",
        OfferingSectionListCreateView.as_view(),
        name="offering-section-list-create",
    ),
    path("sections/<uuid:public_id>/", SectionDetailView.as_view(), name="section-detail"),
]
