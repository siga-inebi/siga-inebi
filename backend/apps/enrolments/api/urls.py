from django.urls import path

from apps.enrolments.api.views import EnrolmentCreateView

urlpatterns = [
    path("", EnrolmentCreateView.as_view(), name="enrolment-list-create"),
]
