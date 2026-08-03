from django.urls import path

from apps.students.api.views import (
    GuardianDetailView,
    GuardianListCreateView,
    StudentDetailView,
    StudentGuardianRelationDetailView,
    StudentGuardianRelationListCreateView,
    StudentListCreateView,
)

urlpatterns = [
    path("", StudentListCreateView.as_view(), name="student-list"),
    path("<int:pk>/", StudentDetailView.as_view(), name="student-detail"),
    path("guardians/", GuardianListCreateView.as_view(), name="guardian-list"),
    path("guardians/<int:pk>/", GuardianDetailView.as_view(), name="guardian-detail"),
    path(
        "guardian-relations/",
        StudentGuardianRelationListCreateView.as_view(),
        name="student-guardian-relation-list",
    ),
    path(
        "guardian-relations/<int:pk>/",
        StudentGuardianRelationDetailView.as_view(),
        name="student-guardian-relation-detail",
    ),
]
