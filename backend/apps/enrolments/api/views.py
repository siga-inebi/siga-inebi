from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.academics.models import AcademicCycle, Grade, Section
from apps.enrolments import services
from apps.enrolments.api.serializers import EnrolmentCreateSerializer, EnrolmentSerializer
from apps.students.models import Student


class EnrolmentCreateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EnrolmentCreateSerializer

    @extend_schema(
        summary="Registrar inscripción",
        description=(
            "Registra una inscripción con estudiante, ciclo, grado, sección y vigencia. "
            "No permite duplicar una inscripción activa en el mismo ciclo."
        ),
        request=EnrolmentCreateSerializer,
        responses={201: EnrolmentSerializer},
        tags=["enrolments"],
    )
    def post(self, request):
        if not request.user.has_atomic_permission("enrollment_create"):
            raise PermissionDenied("Actor lacks the required permission.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        enrolment = services.create_enrolment(
            student=_resolve(Student.objects.all(), payload["student_id"], "Student"),
            academic_cycle=_resolve(
                AcademicCycle.objects.all(), payload["academic_cycle_id"], "Academic cycle"
            ),
            grade=_resolve(Grade.objects.all(), payload["grade_id"], "Grade"),
            section=_resolve(Section.objects.all(), payload["section_id"], "Section"),
            effective_on=payload["effective_on"],
            ends_on=payload.get("ends_on"),
            actor=request.user,
        )
        return Response(EnrolmentSerializer(enrolment).data, status=status.HTTP_201_CREATED)


def _resolve(queryset, public_id, label):
    try:
        return queryset.get(public_id=public_id)
    except queryset.model.DoesNotExist as exc:
        raise NotFound(f"{label} not found.") from exc
