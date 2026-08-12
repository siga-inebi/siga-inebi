from django.urls import path

from apps.attendance.api.views import (
    AttendanceDayStatusView,
    AttendanceEventListCreateView,
    AttendanceEventResolutionView,
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
]
