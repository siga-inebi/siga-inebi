from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.academics.models import AcademicCycle, Grade, Section, Shift
from apps.enrolments import services
from apps.enrolments.api.serializers import (
    EnrolmentCreateSerializer,
    EnrolmentDocumentRequirementCreateSerializer,
    EnrolmentDocumentRequirementSerializer,
    EnrolmentSerializer,
    MatriculationCreateSerializer,
    MatriculationSerializer,
    ReenrolmentCreateSerializer,
)
from apps.enrolments.models import Enrolment
from apps.students.models import Student

_ENROLMENT_WRITE_PERMISSIONS = ("enrollment_create", "enrollment_update")


class EnrolmentCreateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EnrolmentCreateSerializer

    @extend_schema(
        summary="Registrar inscripción",
        description=(
            "Registra una inscripción con estudiante, ciclo, grado, sección y vigencia. "
            "Valida cupo disponible y no permite duplicar una inscripción activa en el "
            "mismo ciclo."
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


class MatriculationCreateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MatriculationCreateSerializer

    @extend_schema(
        summary="Matricular estudiante",
        description=(
            "Matricula un estudiante pre-enrolled y lo vincula al ciclo, grado, jornada y "
            "sección seleccionados despues de validar cupo disponible."
        ),
        request=MatriculationCreateSerializer,
        responses={201: MatriculationSerializer},
        tags=["enrolments"],
    )
    def post(self, request):
        if not request.user.has_atomic_permission("enrollment_create"):
            raise PermissionDenied("Actor lacks the required permission.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        enrolment = services.matriculate_student(
            student=_resolve(Student.objects.all(), payload["student_id"], "Student"),
            academic_cycle=_resolve(
                AcademicCycle.objects.all(), payload["academic_cycle_id"], "Academic cycle"
            ),
            grade=_resolve(Grade.objects.all(), payload["grade_id"], "Grade"),
            shift=_resolve(Shift.objects.all(), payload["shift_id"], "Shift"),
            section=_resolve(Section.objects.all(), payload["section_id"], "Section"),
            effective_on=payload["effective_on"],
            actor=request.user,
        )
        return Response(MatriculationSerializer(enrolment).data, status=status.HTTP_201_CREATED)


class ReenrolmentCreateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReenrolmentCreateSerializer

    @extend_schema(
        summary="Reinscribir estudiante",
        description=(
            "Reinscribe un estudiante activo en un nuevo ciclo reutilizando su expediente "
            "base y la historia de su matricula previa."
        ),
        request=ReenrolmentCreateSerializer,
        responses={201: MatriculationSerializer},
        tags=["enrolments"],
    )
    def post(self, request):
        if not request.user.has_atomic_permission("enrollment_create"):
            raise PermissionDenied("Actor lacks the required permission.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        enrolment = services.reenrol_student(
            student=_resolve(Student.objects.all(), payload["student_id"], "Student"),
            academic_cycle=_resolve(
                AcademicCycle.objects.all(), payload["academic_cycle_id"], "Academic cycle"
            ),
            grade=_resolve(Grade.objects.all(), payload["grade_id"], "Grade"),
            shift=_resolve(Shift.objects.all(), payload["shift_id"], "Shift"),
            section=_resolve(Section.objects.all(), payload["section_id"], "Section"),
            effective_on=payload["effective_on"],
            actor=request.user,
        )
        return Response(MatriculationSerializer(enrolment).data, status=status.HTTP_201_CREATED)


class EnrolmentDocumentRequirementListCreateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Consultar documentos de una matricula",
        responses={200: EnrolmentDocumentRequirementSerializer(many=True)},
        tags=["enrolments"],
    )
    def get(self, request, enrolment_id):
        _ensure_enrolment_permission(request)
        enrolment = _resolve(Enrolment.objects.all(), enrolment_id, "Enrolment")
        requirements = enrolment.document_requirements.filter(is_active=True)
        page = self.paginate_queryset(requirements)
        return self.get_paginated_response(
            EnrolmentDocumentRequirementSerializer(page, many=True).data
        )

    @extend_schema(
        summary="Registrar estado documental de una matricula",
        description="Crea o actualiza el estado de entrega de un documento requerido.",
        request=EnrolmentDocumentRequirementCreateSerializer,
        responses={200: EnrolmentDocumentRequirementSerializer},
        tags=["enrolments"],
    )
    def post(self, request, enrolment_id):
        _ensure_enrolment_permission(request)
        enrolment = _resolve(Enrolment.objects.all(), enrolment_id, "Enrolment")
        serializer = EnrolmentDocumentRequirementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requirement = services.set_document_requirement(
            enrolment=enrolment, actor=request.user, **serializer.validated_data
        )
        return Response(EnrolmentDocumentRequirementSerializer(requirement).data)


def _resolve(queryset, public_id, label):
    try:
        return queryset.get(public_id=public_id)
    except queryset.model.DoesNotExist as exc:
        raise NotFound(f"{label} not found.") from exc


def _ensure_enrolment_permission(request, codenames=_ENROLMENT_WRITE_PERMISSIONS):
    # Registering document state is an upsert over an existing enrolment, so both the
    # create and the update permission are legitimate. The catalogue has no read-only
    # enrolment permission yet, so the listing accepts the same pair.
    if not any(request.user.has_atomic_permission(codename) for codename in codenames):
        raise PermissionDenied("Actor lacks the required permission.")
