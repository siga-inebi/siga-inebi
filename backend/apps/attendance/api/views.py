"""
HTTP layer for Jornada Diaria y Estados.

Views only translate between HTTP and ``apps.attendance.services``; every
invariant lives there (AGENTS.md #8). ``DomainError`` becomes a 400 envelope
via ``config.api.exception_handler``, so no view here catches it.
"""

from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.academics.models import AcademicCycle, Shift
from apps.attendance import services
from apps.attendance.models import JornadaParameters
from apps.common.models import DomainError

from .serializers import JornadaParametersCreateSerializer, JornadaParametersSerializer

CONFIGURE_PERMISSION = "attendance_jornada_configure"


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


def _resolve(queryset, public_id, label):
    """
    Resolve a reference that arrived in the request body. A bad reference in a
    payload is a bad request, not a missing endpoint, so it lands as a 400.
    """
    try:
        return queryset.get(public_id=public_id)
    except queryset.model.DoesNotExist as exc:
        raise DomainError(f"{label} not found.") from exc
