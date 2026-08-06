from django.urls import path

from apps.students.api.views import (
    EmergencyContactDetailView,
    GuardianDetailView,
    GuardianListCreateView,
    StudentDetailView,
    StudentEmergencyContactListCreateView,
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
    # emergency contacts — always created inside a student (RF-EXP-005)
    path(
        "<uuid:public_id>/emergency-contacts/",
        StudentEmergencyContactListCreateView.as_view(),
        name="student-emergency-contact-list-create",
    ),
    path(
        "emergency-contacts/<uuid:public_id>/",
        EmergencyContactDetailView.as_view(),
        name="emergency-contact-detail",
    ),
]
