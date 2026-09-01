"""
URL routing for evaluation API.

Nested under /api/v1/academics/cycles/{cycle_public_id}/evaluation-units/
"""

from django.urls import path

from apps.evaluation.api.views import (
    CaptureExceptionGrantListCreateView,
    EvaluationUnitCloseView,
    EvaluationUnitListCreateView,
    EvaluationUnitRecoveryWindowView,
    GradeListCreateView,
    UnitCaptureProgressView,
)

urlpatterns = [
    path("", EvaluationUnitListCreateView.as_view(), name="evaluation-unit-list"),
    path(
        "<uuid:unit_public_id>/recovery-window/",
        EvaluationUnitRecoveryWindowView.as_view(),
        name="evaluation-unit-recovery-window",
    ),
    path(
        "<uuid:unit_public_id>/close/",
        EvaluationUnitCloseView.as_view(),
        name="evaluation-unit-close",
    ),
    path(
        "<uuid:unit_public_id>/capture-exceptions/",
        CaptureExceptionGrantListCreateView.as_view(),
        name="evaluation-unit-capture-exceptions",
    ),
    path(
        "<uuid:unit_public_id>/grades/",
        GradeListCreateView.as_view(),
        name="evaluation-unit-grades",
    ),
    path(
        "<uuid:unit_public_id>/capture-progress/",
        UnitCaptureProgressView.as_view(),
        name="evaluation-unit-capture-progress",
    ),
]
