"""
API views for evaluation domain.

RF-EVC-001: Estructura de unidades del ciclo

Authorization: requires role=director + permission=evaluation.configure_units
"""

from rest_framework import status
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.response import Response

from apps.academics.models import AcademicCycle
from apps.common.models import DomainError
from apps.evaluation.api.serializers import EvaluationUnitSerializer
from apps.evaluation.models import EvaluationUnit
from apps.evaluation.services import create_evaluation_unit


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
        if not self.request.user or not self.request.user.is_authenticated:
            return False
        # TODO: check for role=director and permission=evaluation.configure_units
        return True

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
            )
        except DomainError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(unit)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
