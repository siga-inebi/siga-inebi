from django.urls import path

from apps.enrolments.api.views import (
    ActiveEnrolmentListView,
    EnrolmentCreateView,
    EnrolmentDocumentRequirementListCreateView,
    EnrolmentHistoryListView,
    MatriculationCreateView,
    ReenrolmentCreateView,
    SectionChangeCreateView,
    SectionOccupancyListView,
    StudentMovementAnnulmentCreateView,
    StudentMovementListView,
    StudentWithdrawalCreateView,
)

urlpatterns = [
    path("active/", ActiveEnrolmentListView.as_view(), name="active-enrolment-list"),
    path("history/", EnrolmentHistoryListView.as_view(), name="enrolment-history-list"),
    path("movements/", StudentMovementListView.as_view(), name="student-movement-list"),
    path(
        "movements/<uuid:movement_id>/annulment/",
        StudentMovementAnnulmentCreateView.as_view(),
        name="student-movement-annulment",
    ),
    path(
        "sections/occupancy/",
        SectionOccupancyListView.as_view(),
        name="section-occupancy-list",
    ),
    path("", EnrolmentCreateView.as_view(), name="enrolment-list-create"),
    path("matriculations/", MatriculationCreateView.as_view(), name="matriculation-create"),
    path("re-enrolments/", ReenrolmentCreateView.as_view(), name="reenrolment-create"),
    path(
        "<uuid:enrolment_id>/section-change/",
        SectionChangeCreateView.as_view(),
        name="enrolment-section-change",
    ),
    path(
        "<uuid:enrolment_id>/withdrawal/",
        StudentWithdrawalCreateView.as_view(),
        name="student-withdrawal",
    ),
    path(
        "<uuid:enrolment_id>/documents/",
        EnrolmentDocumentRequirementListCreateView.as_view(),
        name="enrolment-document-requirement-list-create",
    ),
]
