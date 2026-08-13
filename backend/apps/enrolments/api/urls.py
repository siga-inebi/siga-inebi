from django.urls import path

from apps.enrolments.api.views import (
    EnrolmentCreateView,
    MatriculationCreateView,
    ReenrolmentCreateView,
)

urlpatterns = [
    path("", EnrolmentCreateView.as_view(), name="enrolment-list-create"),
    path("matriculations/", MatriculationCreateView.as_view(), name="matriculation-create"),
    path("re-enrolments/", ReenrolmentCreateView.as_view(), name="reenrolment-create"),
]
