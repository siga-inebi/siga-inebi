from django.urls import path

from apps.attendance.api.views import JornadaParametersListCreateView

urlpatterns = [
    path(
        "jornada-parameters/",
        JornadaParametersListCreateView.as_view(),
        name="attendance-jornada-parameters-list",
    ),
]
