from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, generics, permissions
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.teachers import queries
from apps.teachers.api.serializers import (
    SuggestedEmployeeCodeSerializer,
    TeacherListQuerySerializer,
    TeacherPositionSerializer,
    TeacherSerializer,
)
from apps.teachers.services import deactivate_teacher, next_employee_code


@extend_schema_view(
    get=extend_schema(
        summary="Consultar puestos de docentes y administrativos",
        tags=["teachers"],
        responses={200: TeacherPositionSerializer(many=True)},
    )
)
class TeacherPositionListView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TeacherPositionSerializer
    pagination_class = None

    def get(self, request):
        return Response(self.get_serializer(queries.teacher_positions(), many=True).data)


@extend_schema_view(
    get=extend_schema(
        summary="Sugerir codigo de empleado",
        description=(
            "Siguiente codigo libre de la serie, sin crear nada. El alta lo genera "
            "igual si el campo llega vacio; esto solo permite MOSTRARLO antes de "
            "guardar."
        ),
        tags=["teachers"],
        responses={200: SuggestedEmployeeCodeSerializer},
    )
)
class TeacherNextCodeView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SuggestedEmployeeCodeSerializer

    def get(self, request):
        return Response(
            SuggestedEmployeeCodeSerializer({"employee_code": next_employee_code()}).data
        )


class TeacherActionsContextMixin:
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["teacher_action_permissions"] = queries.teacher_action_permissions(
            actor=self.request.user
        )
        return context


@extend_schema_view(get=extend_schema(parameters=[TeacherListQuerySerializer]))
class TeacherListCreateView(TeacherActionsContextMixin, generics.ListCreateAPIView):
    serializer_class = TeacherSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["employee_code", "person__first_name", "person__last_name", "person__cui"]

    def get_queryset(self):
        params = TeacherListQuerySerializer(data=self.request.query_params.dict())
        params.is_valid(raise_exception=True)
        return queries.teachers(**params.validated_data)


@extend_schema_view(
    delete=extend_schema(
        summary="Desactivar el perfil docente",
        description=(
            "Requiere teacher.deactivate con alcance teachers (o superusuario). "
            "Conserva persona, cuenta, asignaciones y documentos. Es idempotente; "
            "la baja y su auditoría se confirman en una transacción."
        ),
        responses={204: None},
    )
)
class TeacherDetailView(TeacherActionsContextMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TeacherSerializer

    def get_queryset(self):
        return queries.teachers()

    def perform_destroy(self, instance):
        deactivate_teacher(teacher=instance, actor=self.request.user)
