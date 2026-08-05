from django.urls import path

from apps.students.api.views import (
    EmergencyContactDetailView,
    EmergencyContactListCreateView,
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
    path(
        "emergency-contacts/",
        EmergencyContactListCreateView.as_view(),
        name="emergency-contact-list",
    ),
    path(
        "emergency-contacts/<int:pk>/",
        EmergencyContactDetailView.as_view(),
        name="emergency-contact-detail",
    ),
]
