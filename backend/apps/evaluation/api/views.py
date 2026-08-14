"""
API views for evaluation domain.

RF-EVC-001: Estructura de unidades del ciclo
RF-EVC-002: Ventana de captura de notas
RF-EVC-003: Ventana de recuperacion
RF-EVC-004: Brecha excepcional autorizada
RF-EVC-005: Configuracion global heredable

Authorization: requires role=director + permission=evaluation.configure_units
"""

from rest_framework import status
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.academics.models import AcademicCycle
from apps.common.models import DomainError
from apps.evaluation.api.serializers import (
    CaptureExceptionGrantSerializer,
    CycleEvaluationConfigSerializer,
    EvaluationGlobalConfigSerializer,
    EvaluationUnitSerializer,
    RecoveryWindowSerializer,
)
from apps.evaluation.models import CaptureExceptionGrant, EvaluationUnit
from apps.evaluation.services import (
    create_evaluation_unit,
    get_effective_unit_count,
    get_global_evaluation_config,
    grant_capture_exception,
    set_cycle_unit_count,
    set_recovery_window,
    update_global_evaluation_config,
)


class EvaluationUnitListCreateView(ListAPIView, CreateAPIView):
    """
    List and create evaluation units for a cycle.

    GET /api/v1/academics/cycles/{cycle_public_id}/evaluation-units/
    POST /api/v1/academics/cycles/{cycle_public_id}/evaluation-units/
    """

    serializer_class = EvaluationUnitSerializer
    lookup_field = "public_id"

    def get_queryset(self):
        """Filter units by cycle from URL parameter."""
        cycle_public_id = self.kwargs.get("cycle_public_id")
        if cycle_public_id:
            return EvaluationUnit.objects.filter(
                academic_cycle__public_id=cycle_public_id,
                is_active=True,
            ).order_by("number")
        return EvaluationUnit.objects.none()

    def check_director_permission(self):
        """
        Verify user has director role and evaluation.configure_units permission.
        TODO: implement once permission model is complete.
        """
        # For now, require authenticated user; permissions enforced later.
        # TODO: check for role=director and permission=evaluation.configure_units
        return bool(self.request.user and self.request.user.is_authenticated)

    def create(self, request, *args, **kwargs):
        """
        POST /api/v1/academics/cycles/{cycle_public_id}/evaluation-units/

        Creates a new evaluation unit. Only directors can create.
        """
        cycle_public_id = kwargs.get("cycle_public_id")
        if not cycle_public_id:
            return Response(
                {"error": "cycle_public_id required in URL"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not self.check_director_permission():
            return Response(
                {"error": "Permission denied. Only directors can configure evaluation units."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            cycle = AcademicCycle.objects.get(public_id=cycle_public_id)
        except AcademicCycle.DoesNotExist:
            return Response(
                {"error": "Cycle not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            unit = create_evaluation_unit(
                academic_cycle=cycle,
                number=serializer.validated_data["number"],
                name=serializer.validated_data["name"],
                starts_on=serializer.validated_data["starts_on"],
                ends_on=serializer.validated_data["ends_on"],
                capture_starts_on=serializer.validated_data["capture_starts_on"],
                capture_ends_on=serializer.validated_data["capture_ends_on"],
            )
        except DomainError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(unit)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EvaluationUnitRecoveryWindowView(APIView):
    """
    Configure the recovery window of an evaluation unit (RF-EVC-003).

    Base: /api/v1/academics/cycles/{cycle_public_id}/evaluation-units/{unit_public_id}

    PATCH {base}/recovery-window/
    """

    def check_director_permission(self):
        """
        Verify user has director role and evaluation.configure_units permission.
        TODO: implement once permission model is complete.
        """
        # TODO: check for role=director and permission=evaluation.configure_units
        return bool(self.request.user and self.request.user.is_authenticated)

    def patch(self, request, *args, **kwargs):
        if not self.check_director_permission():
            return Response(
                {"error": "Permission denied. Only directors can configure evaluation units."},
                status=status.HTTP_403_FORBIDDEN,
            )

        cycle_public_id = kwargs.get("cycle_public_id")
        unit_public_id = kwargs.get("unit_public_id")

        try:
            unit = EvaluationUnit.objects.get(
                public_id=unit_public_id,
                academic_cycle__public_id=cycle_public_id,
                is_active=True,
            )
        except EvaluationUnit.DoesNotExist:
            return Response(
                {"error": "Evaluation unit not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = RecoveryWindowSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            unit = set_recovery_window(
                unit=unit,
                recovery_starts_on=serializer.validated_data["recovery_starts_on"],
                recovery_ends_on=serializer.validated_data["recovery_ends_on"],
            )
        except DomainError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            EvaluationUnitSerializer(unit).data,
            status=status.HTTP_200_OK,
        )


class CaptureExceptionGrantListCreateView(ListAPIView, CreateAPIView):
    """
    List and grant exceptional capture authorizations for a unit (RF-EVC-004).

    Base: /api/v1/academics/cycles/{cycle_public_id}/evaluation-units/{unit_public_id}

    GET  {base}/capture-exceptions/
    POST {base}/capture-exceptions/
    """

    serializer_class = CaptureExceptionGrantSerializer
    lookup_field = "public_id"

    def check_director_permission(self):
        """
        Verify user has permission for academic authorization.
        TODO: implement once permission model is complete.
        """
        # TODO: check for permission=evaluation.grant_capture_exception
        return bool(self.request.user and self.request.user.is_authenticated)

    def get_queryset(self):
        """Filter grants by unit and cycle from URL parameters."""
        cycle_public_id = self.kwargs.get("cycle_public_id")
        unit_public_id = self.kwargs.get("unit_public_id")
        return CaptureExceptionGrant.objects.filter(
            evaluation_unit__public_id=unit_public_id,
            evaluation_unit__academic_cycle__public_id=cycle_public_id,
            is_active=True,
        )

    def create(self, request, *args, **kwargs):
        """
        POST .../capture-exceptions/

        Grants a new exceptional capture authorization. Only users with
        academic authorization permission can grant one.
        """
        if not self.check_director_permission():
            return Response(
                {
                    "error": (
                        "Permission denied. Only academic authorization can grant "
                        "capture exceptions."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        cycle_public_id = kwargs.get("cycle_public_id")
        unit_public_id = kwargs.get("unit_public_id")

        try:
            unit = EvaluationUnit.objects.get(
                public_id=unit_public_id,
                academic_cycle__public_id=cycle_public_id,
                is_active=True,
            )
        except EvaluationUnit.DoesNotExist:
            return Response(
                {"error": "Evaluation unit not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            grant = grant_capture_exception(
                evaluation_unit=unit,
                subject=serializer.validated_data["subject"],
                teacher=serializer.validated_data["teacher"],
                reason=serializer.validated_data["reason"],
                expires_at=serializer.validated_data["expires_at"],
            )
        except DomainError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(grant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EvaluationGlobalConfigView(APIView):
    """
    Read and update the institution-wide evaluation configuration (RF-EVC-005).

    GET   /api/v1/academics/evaluation-config/
    PATCH /api/v1/academics/evaluation-config/
    """

    def check_director_permission(self):
        """
        Verify user has director role and evaluation.configure_units permission.
        TODO: implement once permission model is complete.
        """
        # TODO: check for role=director and permission=evaluation.configure_units
        return bool(self.request.user and self.request.user.is_authenticated)

    def get(self, request, *args, **kwargs):
        config = get_global_evaluation_config()
        return Response(EvaluationGlobalConfigSerializer(config).data)

    def patch(self, request, *args, **kwargs):
        if not self.check_director_permission():
            return Response(
                {"error": "Permission denied. Only directors can configure evaluation settings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = EvaluationGlobalConfigSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            config = update_global_evaluation_config(
                default_unit_count=serializer.validated_data["default_unit_count"],
            )
        except DomainError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(EvaluationGlobalConfigSerializer(config).data, status=status.HTTP_200_OK)


class CycleEvaluationConfigView(APIView):
    """
    Read the effective unit count and override it for a specific cycle (RF-EVC-005).

    A cycle without its own override inherits the global default. Overriding
    a cycle here never changes the global config nor any other cycle.

    GET   /api/v1/academics/cycles/{cycle_public_id}/evaluation-config/
    PATCH /api/v1/academics/cycles/{cycle_public_id}/evaluation-config/
    """

    def check_director_permission(self):
        """
        Verify user has director role and evaluation.configure_units permission.
        TODO: implement once permission model is complete.
        """
        # TODO: check for role=director and permission=evaluation.configure_units
        return bool(self.request.user and self.request.user.is_authenticated)

    def _get_cycle_or_none(self, cycle_public_id):
        try:
            return AcademicCycle.objects.get(public_id=cycle_public_id)
        except AcademicCycle.DoesNotExist:
            return None

    def get(self, request, *args, **kwargs):
        cycle = self._get_cycle_or_none(kwargs.get("cycle_public_id"))
        if cycle is None:
            return Response({"error": "Cycle not found."}, status=status.HTTP_404_NOT_FOUND)

        override = getattr(cycle, "evaluation_config", None)
        return Response(
            {
                "unit_count": override.unit_count if override else None,
                "effective_unit_count": get_effective_unit_count(cycle),
            }
        )

    def patch(self, request, *args, **kwargs):
        if not self.check_director_permission():
            return Response(
                {"error": "Permission denied. Only directors can configure evaluation settings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        cycle = self._get_cycle_or_none(kwargs.get("cycle_public_id"))
        if cycle is None:
            return Response({"error": "Cycle not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = CycleEvaluationConfigSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            config = set_cycle_unit_count(
                academic_cycle=cycle,
                unit_count=serializer.validated_data["unit_count"],
            )
        except DomainError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "unit_count": config.unit_count,
                "effective_unit_count": get_effective_unit_count(cycle),
            },
            status=status.HTTP_200_OK,
        )
