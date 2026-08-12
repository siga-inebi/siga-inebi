"""
URL routing for evaluation API.

Nested under /api/v1/academics/cycles/{cycle_public_id}/evaluation-units/
"""

from django.urls import path

from apps.evaluation.api.views import (
    EvaluationUnitListCreateView,
    EvaluationUnitRecoveryWindowView,
)

urlpatterns = [
    path("", EvaluationUnitListCreateView.as_view(), name="evaluation-unit-list"),
    path(
        "<uuid:unit_public_id>/recovery-window/",
        EvaluationUnitRecoveryWindowView.as_view(),
        name="evaluation-unit-recovery-window",
    ),
]
