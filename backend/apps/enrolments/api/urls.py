from django.urls import path

from apps.enrolments.api.views import (
    ActiveEnrolmentListView,
    EnrolmentCreateView,
    EnrolmentDocumentRequirementListCreateView,
    EnrolmentHistoryListView,
    MatriculationCreateView,
    ReenrolmentCreateView,
)

urlpatterns = [
    path("active/", ActiveEnrolmentListView.as_view(), name="active-enrolment-list"),
    path("history/", EnrolmentHistoryListView.as_view(), name="enrolment-history-list"),
    path("", EnrolmentCreateView.as_view(), name="enrolment-list-create"),
    path("matriculations/", MatriculationCreateView.as_view(), name="matriculation-create"),
    path("re-enrolments/", ReenrolmentCreateView.as_view(), name="reenrolment-create"),
    path(
        "<uuid:enrolment_id>/documents/",
        EnrolmentDocumentRequirementListCreateView.as_view(),
        name="enrolment-document-requirement-list-create",
    ),
]
