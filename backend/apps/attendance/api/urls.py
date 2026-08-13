from django.urls import path

from apps.attendance.api.views import (
    AttendanceAlertListView,
    AttendanceDayStatusView,
    AttendanceEventListCreateView,
    AttendanceEventResolutionView,
    JornadaClosureView,
    JornadaParametersListCreateView,
)

urlpatterns = [
    path(
        "jornada-parameters/",
        JornadaParametersListCreateView.as_view(),
        name="attendance-jornada-parameters-list",
    ),
    path(
        "events/",
        AttendanceEventListCreateView.as_view(),
        name="attendance-event-list",
    ),
    path(
        "events/resolution/",
        AttendanceEventResolutionView.as_view(),
        name="attendance-event-resolution",
    ),
    path(
        "day-status/",
        AttendanceDayStatusView.as_view(),
        name="attendance-day-status",
    ),
    path(
        "jornada-closures/",
        JornadaClosureView.as_view(),
        name="attendance-jornada-closures",
    ),
    path(
        "alerts/",
        AttendanceAlertListView.as_view(),
        name="attendance-alert-list",
    ),
]
