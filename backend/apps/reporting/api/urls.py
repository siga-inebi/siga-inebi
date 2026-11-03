from django.urls import path

from apps.reporting.api.views import (
    AbsenceThresholdParametersListCreateView,
    AlertEvaluationView,
    ReportingAlertAcknowledgeView,
    ReportingAlertListView,
)

urlpatterns = [
    path(
        "absence-threshold-parameters/",
        AbsenceThresholdParametersListCreateView.as_view(),
        name="reporting-absence-threshold-parameters-list",
    ),
    path(
        "alerts/",
        ReportingAlertListView.as_view(),
        name="reporting-alert-list",
    ),
    path(
        "alerts/<uuid:public_id>/acknowledge/",
        ReportingAlertAcknowledgeView.as_view(),
        name="reporting-alert-acknowledge",
    ),
    path(
        "alert-evaluations/",
        AlertEvaluationView.as_view(),
        name="reporting-alert-evaluations",
    ),
]
