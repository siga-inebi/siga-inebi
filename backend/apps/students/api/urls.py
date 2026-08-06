from django.urls import path

from apps.students.api.views import (
    EmergencyContactDetailView,
    GuardianDetailView,
    GuardianListCreateView,
    GuardianOptionListView,
    StudentDetailView,
    StudentEmergencyContactListCreateView,
    StudentGuardianRelationDetailView,
    StudentGuardianRelationListCreateView,
    StudentListCreateView,
)

urlpatterns = [
    path("", StudentListCreateView.as_view(), name="student-list"),
    path("<int:pk>/", StudentDetailView.as_view(), name="student-detail"),
    # guardian options must come before the pk-based detail route below it
    # would otherwise never be reached for the literal segment "options"
    # (int converter never matches it anyway, but the order stays explicit).
    path("guardians/options/", GuardianOptionListView.as_view(), name="guardian-option-list"),
    path("guardians/", GuardianListCreateView.as_view(), name="guardian-list"),
    path("guardians/<int:pk>/", GuardianDetailView.as_view(), name="guardian-detail"),
    # guardian relations — always created inside a student (RF-EXP-004)
    path(
        "<uuid:public_id>/guardian-relations/",
        StudentGuardianRelationListCreateView.as_view(),
        name="student-guardian-relation-list-create",
    ),
    path(
        "guardian-relations/<uuid:public_id>/",
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
