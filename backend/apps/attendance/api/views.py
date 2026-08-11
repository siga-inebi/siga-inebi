"""
HTTP layer for Jornada Diaria y Estados.

Views only translate between HTTP and ``apps.attendance.services``; every
invariant lives there (AGENTS.md #8). ``DomainError`` becomes a 400 envelope
via ``config.api.exception_handler``, so no view here catches it.
"""

from rest_framework import permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.academics.models import AcademicCycle, Shift
from apps.attendance import services
from apps.attendance.models import AttendanceEvent, JornadaParameters
from apps.common.models import DomainError
from apps.identity.scopes import authorized_student_queryset, can_access_student
from apps.students.models import Student

from .serializers import (
    AttendanceEventCreateSerializer,
    AttendanceEventResolutionQuerySerializer,
    AttendanceEventSerializer,
    DayStatusQuerySerializer,
    DayStatusResultSerializer,
    JornadaParametersCreateSerializer,
    JornadaParametersSerializer,
)

CONFIGURE_PERMISSION = "attendance_jornada_configure"
STUDENT_VIEW_PERMISSION = "student_view_basic"

# Provisional: one atomic permission per event origin. A separate
# attendance-capture effort owns the real scanning/ingestion workflow and may
# replace this mapping; this skeleton exists only so RF-JOR-002/003 have
# events to read (see tmp/attendance_basis.md).
ORIGIN_PERMISSIONS = {
    AttendanceEvent.Origin.SCAN: "attendance_scan",
    AttendanceEvent.Origin.MANUAL: "attendance_record_manual",
    AttendanceEvent.Origin.DECLARED: "attendance_declared_close",
}


class JornadaParametersListCreateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = JornadaParametersSerializer

    def get_queryset(self):
        return JornadaParameters.objects.select_related("shift", "academic_cycle").all()

    def get(self, request):
        self._require_configure_permission()
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(JornadaParametersSerializer(page, many=True).data)

    def post(self, request):
        self._require_configure_permission()
        serializer = JornadaParametersCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        shift = _resolve(Shift.objects.all(), payload.pop("shift_id"), "Shift")
        academic_cycle = _resolve(
            AcademicCycle.objects.all(), payload.pop("academic_cycle_id"), "Academic cycle"
        )
        parameters = services.set_jornada_parameters(
            shift=shift, academic_cycle=academic_cycle, actor=request.user, **payload
        )
        return Response(
            JornadaParametersSerializer(parameters).data, status=status.HTTP_201_CREATED
        )

    def _require_configure_permission(self):
        if not self.request.user.has_atomic_permission(CONFIGURE_PERMISSION):
            raise PermissionDenied("Actor lacks the required permission.")


class AttendanceEventListCreateView(GenericAPIView):
    """Deliberately thin skeleton: see ``ORIGIN_PERMISSIONS`` above."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttendanceEventSerializer

    def get_queryset(self):
        return AttendanceEvent.objects.filter(
            student__in=authorized_student_queryset(
                user=self.request.user, codename=STUDENT_VIEW_PERMISSION
            )
        ).select_related("student", "shift")

    def get(self, request):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(AttendanceEventSerializer(page, many=True).data)

    def post(self, request):
        serializer = AttendanceEventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        codename = ORIGIN_PERMISSIONS[payload["origin"]]
        if not request.user.has_atomic_permission(codename):
            raise PermissionDenied("Actor lacks the required permission.")
        student = _resolve(Student.objects.all(), payload.pop("student_id"), "Student")
        shift = _resolve(Shift.objects.all(), payload.pop("shift_id"), "Shift")
        event = services.record_attendance_event(
            student=student, shift=shift, actor=request.user, **payload
        )
        return Response(AttendanceEventSerializer(event).data, status=status.HTTP_201_CREATED)


class AttendanceEventResolutionView(GenericAPIView):
    """RF-JOR-003 contract: the event that prevails by precedence."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttendanceEventSerializer

    def get(self, request):
        query = AttendanceEventResolutionQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        payload = query.validated_data
        student = _resolve(Student.objects.all(), payload["student_id"], "Student")
        shift = _resolve(Shift.objects.all(), payload["shift_id"], "Shift")
        if not can_access_student(
            user=request.user, codename=STUDENT_VIEW_PERMISSION, student=student
        ):
            raise PermissionDenied("Actor lacks the required permission or student scope.")
        event = services.resolve_prevailing_event(
            student=student,
            shift=shift,
            event_date=payload["event_date"],
            movement_type=payload["movement_type"],
        )
        if event is None:
            raise NotFound("No attendance event found for the given criteria.")
        return Response(AttendanceEventSerializer(event).data)


class AttendanceDayStatusView(GenericAPIView):
    """RF-JOR-002 contract: derive a student's daily status for a jornada."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DayStatusResultSerializer

    def get(self, request):
        query = DayStatusQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        payload = query.validated_data
        student = _resolve(Student.objects.all(), payload["student_id"], "Student")
        shift = _resolve(Shift.objects.all(), payload["shift_id"], "Shift")
        if not can_access_student(
            user=request.user, codename=STUDENT_VIEW_PERMISSION, student=student
        ):
            raise PermissionDenied("Actor lacks the required permission or student scope.")
        result = services.derive_day_status(
            student=student, shift=shift, event_date=payload["event_date"]
        )
        if result is None:
            return Response({"status": None, "entry_event": None})
        return Response(DayStatusResultSerializer(result).data)


def _resolve(queryset, public_id, label):
    """
    Resolve a reference that arrived in the request body. A bad reference in a
    payload is a bad request, not a missing endpoint, so it lands as a 400.
    """
    try:
        return queryset.get(public_id=public_id)
    except queryset.model.DoesNotExist as exc:
        raise DomainError(f"{label} not found.") from exc
