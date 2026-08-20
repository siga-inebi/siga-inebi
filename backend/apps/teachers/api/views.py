from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.teachers.api.serializers import (
    SuggestedEmployeeCodeSerializer,
    TeacherSerializer,
)
from apps.teachers.models import Teacher
from apps.teachers.services import deactivate_teacher, next_employee_code


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


class TeacherListCreateView(generics.ListCreateAPIView):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer


class TeacherDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer

    def perform_destroy(self, instance):
        deactivate_teacher(teacher=instance, actor=self.request.user)
