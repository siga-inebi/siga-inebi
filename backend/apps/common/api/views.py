"""
HTTP layer for the operational monitoring surface (RNF-OPE-001).

Read-only on purpose: a task run is history written by whoever executed the
task, and nothing over HTTP may create, edit or erase one (RN-BIT-001). Both
operations require ``platform_monitor``, the permission of the actor the
requirement names -- the system administrator.
"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions
from rest_framework.generics import GenericAPIView

from apps.common import backups, queries, services

from .serializers import (
    BackupStackHealthSerializer,
    TaskHealthSerializer,
    TaskRunQuerySerializer,
    TaskRunSerializer,
)

TAGS = ["platform: operacion"]


@extend_schema_view(
    get=extend_schema(
        summary="Listar ejecuciones de tareas en segundo plano",
        description=(
            "Historial de ejecuciones de tareas programadas y en segundo plano, mas "
            "reciente primero (RNF-OPE-001). Filtros opcionales por nombre y estado. "
            "Requiere el permiso `platform.monitor`."
        ),
        tags=TAGS,
        parameters=[TaskRunQuerySerializer],
        responses={200: TaskRunSerializer(many=True)},
    ),
)
class TaskRunListView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskRunSerializer

    def get(self, request):
        services.ensure_platform_monitor_permission(actor=request.user)
        query = TaskRunQuerySerializer(data=request.query_params.dict())
        query.is_valid(raise_exception=True)
        page = self.paginate_queryset(
            queries.task_runs(
                name=query.validated_data.get("name"),
                status=query.validated_data.get("status"),
            )
        )
        return self.get_paginated_response(self.get_serializer(page, many=True).data)


@extend_schema_view(
    get=extend_schema(
        summary="Estado de las tareas en segundo plano",
        description=(
            "Una fila por tarea conocida con su ultima ejecucion y el conteo de fallos "
            "(RNF-OPE-001). Requiere el permiso `platform.monitor`."
        ),
        tags=TAGS,
        responses={200: TaskHealthSerializer(many=True)},
    ),
)
class TaskHealthView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskHealthSerializer

    def get(self, request):
        summary = services.task_health_summary(actor=request.user)
        page = self.paginate_queryset(summary)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)


@extend_schema_view(
    get=extend_schema(
        summary="Estado de los respaldos frente al RPO declarado",
        description=(
            "Una fila por pila de respaldo, base de datos y archivos, nunca agregadas: "
            "los dos esquemas son independientes (RNF-RES-001). `meets_rpo` compara la "
            "edad del respaldo mas reciente contra el RPO declarado (RNF-RES-002). "
            "Requiere el permiso `platform.monitor`."
        ),
        tags=TAGS,
        responses={200: BackupStackHealthSerializer(many=True)},
    ),
)
class BackupHealthView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BackupStackHealthSerializer

    def get(self, request):
        services.ensure_platform_monitor_permission(actor=request.user)
        page = self.paginate_queryset(backups.backup_health())
        return self.get_paginated_response(self.get_serializer(page, many=True).data)
