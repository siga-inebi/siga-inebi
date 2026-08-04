"""
HTTP layer for the academic catalogue.

Views only translate between HTTP and the domain services in
``apps.academics.services``; every invariant lives there. ``DomainError`` is
turned into a 400 envelope by ``config.api.exception_handler``, so no view
catches it (AGENTS.md #8).

The request/response plumbing is identical for every resource, so it lives once
in the base classes below. Each concrete view declares its serializers and the
two or three lines that are genuinely its own: which queryset it lists, and
which service it calls. OpenAPI text is attached with ``extend_schema_view`` so
the docs stay per-resource even though the handlers are inherited.
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.academics import services
from apps.academics.api import queries

from .serializers import (
    CampusCreateSerializer,
    CampusSerializer,
    CampusUpdateSerializer,
    ShiftCreateSerializer,
    ShiftSerializer,
    ShiftUpdateSerializer,
)

CATALOGUE = ["academics: catalogue"]

INCLUDE_INACTIVE = OpenApiParameter(
    name="include_inactive",
    type=bool,
    location=OpenApiParameter.QUERY,
    required=False,
    description="Incluye registros desactivados. Por defecto solo se listan los activos.",
)


# --------------------------------------------------------------------------- #
# base classes
# --------------------------------------------------------------------------- #


class CatalogueView(GenericAPIView):
    """Authenticated access plus the institution the request operates on."""

    permission_classes = [permissions.IsAuthenticated]

    @property
    def institution(self):
        if not hasattr(self, "_institution"):
            self._institution = queries.resolve_institution(self.request)
        return self._institution

    def validated(self, serializer_class, request):
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class CatalogueListCreateView(CatalogueView):
    """
    ``GET`` lists a queryset, paginated; ``POST`` delegates to a service.

    Subclasses provide ``list_serializer``, ``create_serializer``,
    ``list_queryset(request, **kwargs)`` and ``create(request, payload, **kwargs)``.
    """

    list_serializer = None
    create_serializer = None

    def get_serializer_class(self):
        if self.request.method == "POST":
            return self.create_serializer
        return self.list_serializer

    def get(self, request, **kwargs):
        page = self.paginate_queryset(self.list_queryset(request, **kwargs))
        return self.get_paginated_response(self.list_serializer(page, many=True).data)

    def post(self, request, **kwargs):
        payload = self.validated(self.create_serializer, request)
        created = self.create(request, payload, **kwargs)
        return Response(self.list_serializer(created).data, status=status.HTTP_201_CREATED)


class CatalogueDetailView(CatalogueView):
    """Subclasses provide ``detail_serializer`` and ``get_object(**kwargs)``."""

    detail_serializer = None
    update_serializer = None

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return self.update_serializer
        return self.detail_serializer

    def represent(self, instance):
        return Response(self.detail_serializer(instance).data)


class RetrieveMixin:
    def get(self, request, **kwargs):
        return self.represent(self.get_object(**kwargs))


class UpdateMixin:
    """``PATCH`` re-reads the object so annotated counts stay in the response."""

    def patch(self, request, **kwargs):
        payload = self.validated(self.update_serializer, request)
        self.update(request, self.get_object(**kwargs), payload)
        return self.represent(self.get_object(**kwargs))


class DeactivateMixin:
    def delete(self, request, **kwargs):
        self.deactivate(request, self.get_object(**kwargs))
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------- #
# campuses ("sedes")
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar sedes",
        description="Sedes de la institucion. Solo activas salvo `include_inactive=true`.",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE],
        responses={200: CampusSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Crear sede",
        description=(
            "Registra una sede. El codigo se normaliza a mayusculas y es unico por "
            "institucion. Marcar `is_main` degrada la sede principal anterior."
        ),
        tags=CATALOGUE,
        request=CampusCreateSerializer,
        responses={201: CampusSerializer},
    ),
)
class CampusListCreateView(CatalogueListCreateView):
    list_serializer = CampusSerializer
    create_serializer = CampusCreateSerializer

    def list_queryset(self, request):
        return queries.campuses(self.institution, request)

    def create(self, request, payload):
        campus = services.create_campus(institution=self.institution, actor=request.user, **payload)
        return queries.campus_or_404(self.institution, campus.public_id)


@extend_schema_view(
    get=extend_schema(summary="Consultar sede", tags=CATALOGUE, responses={200: CampusSerializer}),
    patch=extend_schema(
        summary="Actualizar sede",
        description="El codigo es inmutable; se actualizan nombre, direccion y sede principal.",
        tags=CATALOGUE,
        request=CampusUpdateSerializer,
        responses={200: CampusSerializer},
    ),
    delete=extend_schema(
        summary="Desactivar sede",
        description=(
            "Desactiva la sede y sus jornadas en lugar de borrarlas (RF-EST-012). "
            "Se rechaza si un ciclo no cerrado usa alguna de sus jornadas."
        ),
        tags=CATALOGUE,
        responses={204: None},
    ),
)
class CampusDetailView(RetrieveMixin, UpdateMixin, DeactivateMixin, CatalogueDetailView):
    detail_serializer = CampusSerializer
    update_serializer = CampusUpdateSerializer

    def get_object(self, public_id):
        return queries.campus_or_404(self.institution, public_id)

    def update(self, request, campus, payload):
        services.update_campus(campus=campus, actor=request.user, **payload)

    def deactivate(self, request, campus):
        services.deactivate_campus(campus=campus, actor=request.user)


# --------------------------------------------------------------------------- #
# shifts ("jornadas") — always under a campus
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar jornadas de una sede",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE],
        responses={200: ShiftSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Crear jornada en una sede",
        description=(
            "El codigo es unico dentro de la sede, de modo que dos sedes pueden tener MAT."
        ),
        tags=CATALOGUE,
        request=ShiftCreateSerializer,
        responses={201: ShiftSerializer},
    ),
)
class CampusShiftListCreateView(CatalogueListCreateView):
    list_serializer = ShiftSerializer
    create_serializer = ShiftCreateSerializer

    def list_queryset(self, request, public_id):
        return queries.shifts(queries.campus_or_404(self.institution, public_id), request)

    def create(self, request, payload, public_id):
        campus = queries.campus_or_404(self.institution, public_id)
        return services.create_shift(campus=campus, actor=request.user, **payload)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar jornada", tags=CATALOGUE, responses={200: ShiftSerializer}
    ),
    patch=extend_schema(
        summary="Renombrar jornada",
        tags=CATALOGUE,
        request=ShiftUpdateSerializer,
        responses={200: ShiftSerializer},
    ),
    delete=extend_schema(
        summary="Desactivar jornada",
        description="Se rechaza si un ciclo no cerrado oferta grados en esta jornada.",
        tags=CATALOGUE,
        responses={204: None},
    ),
)
class ShiftDetailView(RetrieveMixin, UpdateMixin, DeactivateMixin, CatalogueDetailView):
    detail_serializer = ShiftSerializer
    update_serializer = ShiftUpdateSerializer

    def get_object(self, public_id):
        return queries.shift_or_404(self.institution, public_id)

    def update(self, request, shift, payload):
        services.update_shift(shift=shift, actor=request.user, **payload)

    def deactivate(self, request, shift):
        services.deactivate_shift(shift=shift, actor=request.user)
