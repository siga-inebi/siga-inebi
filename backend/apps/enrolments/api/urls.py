from django.urls import path

from .views import (
    EnrolmentChangeSectionView,
    EnrolmentListCreateView,
    EnrolmentReenrolView,
    EnrolmentWithdrawView,
)

urlpatterns = [
    path("", EnrolmentListCreateView.as_view(), name="enrolment-list-create"),
    path(
        "<uuid:public_id>/withdraw/",
        EnrolmentWithdrawView.as_view(),
        name="enrolment-withdraw",
    ),
    path(
        "<uuid:public_id>/reenrol/",
        EnrolmentReenrolView.as_view(),
        name="enrolment-reenrol",
    ),
    path(
        "<uuid:public_id>/change-section/",
        EnrolmentChangeSectionView.as_view(),
        name="enrolment-change-section",
    ),
]
