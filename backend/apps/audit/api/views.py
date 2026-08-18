"""
HTTP layer for Consulta y exportacion restringidas de la bitacora (RF-BIT-006).

Views only translate between HTTP and ``apps.audit.services``; the filtering
rule lives there (AGENTS.md #8). Both operations require the same
``audit_read`` atomic permission -- the criterio restricts consulta and
exportacion equally to "usuarios con permiso de auditoria", and no other
audit-specific permission exists in the catalogue yet.

These handlers are written by hand on ``GenericAPIView``, so drf-spectacular
cannot infer their contract from ``serializer_class`` alone; every operation
declares it with ``extend_schema`` so the published schema matches what the
endpoint really accepts and returns.
"""

import csv
import io

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import GenericAPIView

from apps.audit import services

from .serializers import AuditEventQuerySerializer, AuditEventSerializer

AUDIT_READ_PERMISSION = "audit_read"

TAGS = ["audit: bitacora"]


def _require_permission(request, codename):
    if not request.user.has_atomic_permission(codename):
        raise PermissionDenied("Actor lacks the required permission.")


def _query_filters(request):
    query = AuditEventQuerySerializer(data=request.query_params.dict())
    query.is_valid(raise_exception=True)
    return query.validated_data


@extend_schema_view(
    get=extend_schema(
        summary="Listar asientos de bitacora",
        description=(
            "Consulta restringida a usuarios con permiso de auditoria. Todos los "
            "filtros son opcionales: usuario, capacidad afectada, tipo de accion y "
            "rango de fechas."
        ),
        tags=TAGS,
        parameters=[AuditEventQuerySerializer],
        responses={200: AuditEventSerializer(many=True)},
    ),
)
class AuditEventListView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AuditEventSerializer

    def get(self, request):
        _require_permission(request, AUDIT_READ_PERMISSION)
        payload = _query_filters(request)
        queryset = services.list_audit_events(**payload)
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(AuditEventSerializer(page, many=True).data)


@extend_schema_view(
    get=extend_schema(
        summary="Exportar asientos de bitacora",
        description=(
            "Genera un CSV del rango filtrado y registra la exportacion en la "
            "bitacora con el usuario, el rango y el momento."
        ),
        tags=TAGS,
        parameters=[AuditEventQuerySerializer],
        responses={200: OpenApiTypes.BINARY},
    ),
)
class AuditEventExportView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AuditEventSerializer

    def get(self, request):
        _require_permission(request, AUDIT_READ_PERMISSION)
        payload = _query_filters(request)
        queryset = services.list_audit_events(**payload)

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            ["created_at", "actor", "action", "resource", "resource_identifier", "ip_address"]
        )
        count = 0
        for event in queryset:
            writer.writerow(
                [
                    event.created_at.isoformat(),
                    event.actor_label,
                    event.action,
                    event.resource,
                    event.resource_identifier,
                    event.ip_address or "",
                ]
            )
            count += 1

        services.record_audit_export(
            actor=request.user,
            date_from=payload.get("date_from"),
            date_to=payload.get("date_to"),
            count=count,
        )

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="audit-events.csv"'
        return response
