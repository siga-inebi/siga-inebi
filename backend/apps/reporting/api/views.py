"""
HTTP layer for Alertas de asistencia (RF-JOR-007).

Views only translate between HTTP and ``apps.reporting.services``; every
invariant lives there (AGENTS.md #8). ``DomainError`` becomes a 400 envelope
via ``config.api.exception_handler``, so no view here catches it.
"""

from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.academics.models import AcademicCycle, Shift
from apps.common.models import DomainError
from apps.identity.scopes import authorized_student_queryset, can_access_student
from apps.reporting import services
from apps.reporting.models import AbsenceThresholdParameters, Alert

from .serializers import (
    AbsenceThresholdParametersCreateSerializer,
    AbsenceThresholdParametersSerializer,
    AlertEvaluationRequestSerializer,
    DailyAlertEvaluationResultSerializer,
    ReportingAlertQuerySerializer,
    ReportingAlertSerializer,
)

ALERT_VIEW_PERMISSION = "reporting_alert_view"
ALERT_ACKNOWLEDGE_PERMISSION = "reporting_alert_acknowledge"
ALERT_EVALUATE_PERMISSION = "reporting_alert_evaluate"
THRESHOLD_CONFIGURE_PERMISSION = "reporting_absence_threshold_configure"
STUDENT_VIEW_PERMISSION = "student_view_basic"


def _require_permission(request, codename):
    if not request.user.has_atomic_permission(codename):
        raise PermissionDenied("Actor lacks the required permission.")


def _resolve(queryset, public_id, label):
    """
    Resolve a reference that arrived in the request. A bad reference is a
    bad request, not a missing endpoint, so it lands as a 400.
    """
    try:
        return queryset.get(public_id=public_id)
    except queryset.model.DoesNotExist as exc:
        raise DomainError(f"{label} not found.") from exc


class AbsenceThresholdParametersListCreateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AbsenceThresholdParametersSerializer

    def get_queryset(self):
        return AbsenceThresholdParameters.objects.select_related("shift", "academic_cycle").all()

    def get(self, request):
        _require_permission(request, THRESHOLD_CONFIGURE_PERMISSION)
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(
            AbsenceThresholdParametersSerializer(page, many=True).data
        )

    def post(self, request):
        _require_permission(request, THRESHOLD_CONFIGURE_PERMISSION)
        serializer = AbsenceThresholdParametersCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        shift = _resolve(Shift.objects.all(), payload.pop("shift_id"), "Shift")
        academic_cycle = _resolve(
            AcademicCycle.objects.all(), payload.pop("academic_cycle_id"), "Academic cycle"
        )
        parameters = services.set_absence_threshold_parameters(
            shift=shift, academic_cycle=academic_cycle, actor=request.user, **payload
        )
        return Response(
            AbsenceThresholdParametersSerializer(parameters).data, status=status.HTTP_201_CREATED
        )


class ReportingAlertListView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReportingAlertSerializer

    def get(self, request):
        _require_permission(request, ALERT_VIEW_PERMISSION)
        # ``.dict()`` strips QueryDict's HTML-form semantics: left as a
        # QueryDict, DRF's BooleanField treats an absent key as an unchecked
        # checkbox (False) instead of "not provided".
        query = ReportingAlertQuerySerializer(data=request.query_params.dict())
        query.is_valid(raise_exception=True)
        payload = query.validated_data

        shift = None
        if "shift_id" in payload:
            shift = _resolve(Shift.objects.all(), payload["shift_id"], "Shift")

        queryset = services.list_alerts(
            shift=shift,
            event_date=payload.get("event_date"),
            alert_type=payload.get("alert_type"),
            is_active=payload.get("is_active"),
            acknowledged=payload.get("acknowledged"),
        ).filter(
            student__in=authorized_student_queryset(
                user=request.user, codename=STUDENT_VIEW_PERMISSION
            )
        )
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(ReportingAlertSerializer(page, many=True).data)


class ReportingAlertAcknowledgeView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReportingAlertSerializer

    def post(self, request, public_id):
        _require_permission(request, ALERT_ACKNOWLEDGE_PERMISSION)
        alert = _resolve(Alert.objects.select_related("student"), public_id, "Alert")
        # Holding the acknowledge permission is not enough: the alert is
        # about a student, so the actor's student scope decides too, the same
        # way the list view above and attendance's own single-resource
        # endpoints do it. Without this an actor scoped to one section can
        # attend alerts of the whole institution.
        if not can_access_student(
            user=request.user, codename=STUDENT_VIEW_PERMISSION, student=alert.student
        ):
            raise PermissionDenied("Actor lacks the required permission or student scope.")
        alert = services.acknowledge_alert(alert=alert, actor=request.user)
        return Response(ReportingAlertSerializer(alert).data)


class AlertEvaluationView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DailyAlertEvaluationResultSerializer

    def post(self, request):
        _require_permission(request, ALERT_EVALUATE_PERMISSION)
        serializer = AlertEvaluationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        shift = _resolve(Shift.objects.all(), payload["shift_id"], "Shift")
        result = services.evaluate_daily_alerts(
            shift=shift, event_date=payload["event_date"], actor=request.user
        )
        return Response(DailyAlertEvaluationResultSerializer(result).data)
