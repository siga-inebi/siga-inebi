"""
URL routing for evaluation API.

Nested under /api/v1/academics/cycles/{cycle_public_id}/evaluation-units/
"""

from django.urls import path

from apps.evaluation.api.views import EvaluationUnitListCreateView

urlpatterns = [
    path("", EvaluationUnitListCreateView.as_view(), name="evaluation-unit-list"),
]
