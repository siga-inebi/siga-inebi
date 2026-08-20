from django.urls import path

from apps.students.api.views import (
    EmergencyContactDetailView,
    GuardianDetailView,
    GuardianListCreateView,
    StudentDetailView,
    StudentEmergencyContactListCreateView,
    StudentGuardianRelationDetailView,
    StudentGuardianRelationEndView,
    StudentGuardianRelationListCreateView,
    StudentGuardianRelationPrimaryView,
    StudentHealthNoteDetailView,
    StudentHealthNoteListCreateView,
    StudentListCreateView,
    StudentNextCodeView,
    StudentObservationDetailView,
    StudentObservationListCreateView,
)

urlpatterns = [
    path("", StudentListCreateView.as_view(), name="student-list"),
    path("next-code/", StudentNextCodeView.as_view(), name="student-next-code"),
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
        "guardian-relations/<int:pk>/make-primary/",
        StudentGuardianRelationPrimaryView.as_view(),
        name="student-guardian-relation-make-primary",
    ),
    path(
        "guardian-relations/<int:pk>/end/",
        StudentGuardianRelationEndView.as_view(),
        name="student-guardian-relation-end",
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
    path(
        "<uuid:public_id>/health-notes/",
        StudentHealthNoteListCreateView.as_view(),
        name="student-health-note-list-create",
    ),
    path(
        "health-notes/<uuid:public_id>/",
        StudentHealthNoteDetailView.as_view(),
        name="student-health-note-detail",
    ),
    path(
        "<uuid:public_id>/observations/",
        StudentObservationListCreateView.as_view(),
        name="student-observation-list-create",
    ),
    path(
        "observations/<uuid:public_id>/",
        StudentObservationDetailView.as_view(),
        name="student-observation-detail",
    ),
]
