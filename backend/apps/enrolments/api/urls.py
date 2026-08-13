from django.urls import path

from apps.enrolments.api.views import (
    EnrolmentCreateView,
    EnrolmentHistoryListView,
    MatriculationCreateView,
)

urlpatterns = [
    path("history/", EnrolmentHistoryListView.as_view(), name="enrolment-history-list"),
    path("", EnrolmentCreateView.as_view(), name="enrolment-list-create"),
    path("matriculations/", MatriculationCreateView.as_view(), name="matriculation-create"),
]
