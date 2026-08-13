from django.urls import path

from apps.enrolments.api.views import (
    ActiveEnrolmentListView,
    EnrolmentCreateView,
    MatriculationCreateView,
)

urlpatterns = [
    path("active/", ActiveEnrolmentListView.as_view(), name="active-enrolment-list"),
    path("", EnrolmentCreateView.as_view(), name="enrolment-list-create"),
    path("matriculations/", MatriculationCreateView.as_view(), name="matriculation-create"),
]
