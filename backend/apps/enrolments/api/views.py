from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.common.exceptions import AuthorizationError
from apps.enrolments import queries, services
from apps.enrolments.api.serializers import (
    ActiveEnrolmentQuerySerializer,
    EnrolmentCreateSerializer,
    EnrolmentDocumentRequirementCreateSerializer,
    EnrolmentDocumentRequirementSerializer,
    EnrolmentHistoryQuerySerializer,
    EnrolmentSerializer,
    MatriculationCreateSerializer,
    MatriculationSerializer,
    ReenrolmentCreateSerializer,
    SectionChangeCreateSerializer,
    SectionOccupancyQuerySerializer,
    SectionOccupancySerializer,
    StudentMovementQuerySerializer,
    StudentMovementSerializer,
    StudentWithdrawalCreateSerializer,
)

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
            raise AuthorizationError("Actor lacks the required permission.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        enrolment = services.create_enrolment(
            student=queries.student_or_404(payload["student_id"]),
            academic_cycle=queries.academic_cycle_or_404(payload["academic_cycle_id"]),
            grade=queries.grade_or_404(payload["grade_id"]),
            section=queries.section_or_404(payload["section_id"]),
            effective_on=payload["effective_on"],
            ends_on=payload.get("ends_on"),
            actor=request.user,
        )
        return Response(EnrolmentSerializer(enrolment).data, status=status.HTTP_201_CREATED)


class ActiveEnrolmentListView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ActiveEnrolmentQuerySerializer

    @extend_schema(
        summary="Listar inscripciones activas",
        description=(
            "Devuelve la fuente vigente de estudiantes habilitados para asistencia, "
            "notas y horarios. Puede filtrarse por estudiante."
        ),
        parameters=[ActiveEnrolmentQuerySerializer],
        responses={200: EnrolmentSerializer(many=True)},
        tags=["enrolments"],
    )
    def get(self, request):
        query = self.get_serializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        student = None
        student_id = query.validated_data.get("student_id")
        if student_id:
            student = queries.student_or_404(student_id)
        page = self.paginate_queryset(services.active_enrolments(student=student))
        return self.get_paginated_response(EnrolmentSerializer(page, many=True).data)


class SectionOccupancyListView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SectionOccupancyQuerySerializer

    @extend_schema(
        summary="Consultar cupo y ocupación por sección",
        description=(
            "Cupo maximo declarado y ocupacion en tiempo real (vacantes disponibles y "
            "utilizadas) por seccion. Filtra opcionalmente por ciclo, grado o una sola "
            "seccion. Solo secciones activas salvo `include_inactive=true`."
        ),
        parameters=[SectionOccupancyQuerySerializer],
        responses={200: SectionOccupancySerializer(many=True)},
        tags=["enrolments"],
    )
    def get(self, request):
        query = self.get_serializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        payload = query.validated_data

        academic_cycle_id = payload.get("academic_cycle_id")
        academic_cycle = (
            queries.academic_cycle_or_404(academic_cycle_id) if academic_cycle_id else None
        )
        grade_id = payload.get("grade_id")
        grade = queries.grade_or_404(grade_id) if grade_id else None
        section_id = payload.get("section_id")
        section = queries.section_or_404(section_id) if section_id else None

        page = self.paginate_queryset(
            services.section_occupancy(
                academic_cycle=academic_cycle,
                grade=grade,
                section=section,
                include_inactive=payload.get("include_inactive", False),
            )
        )
        return self.get_paginated_response(SectionOccupancySerializer(page, many=True).data)


class EnrolmentHistoryListView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EnrolmentHistoryQuerySerializer

    @extend_schema(
        summary="Consultar historial de inscripciones",
        description=(
            "Devuelve todas las inscripciones registradas para un estudiante, "
            "incluyendo estados históricos y vigencias anteriores."
        ),
        parameters=[EnrolmentHistoryQuerySerializer],
        responses={200: EnrolmentSerializer(many=True)},
        tags=["enrolments"],
    )
    def get(self, request):
        query = self.get_serializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        student = queries.student_or_404(query.validated_data["student_id"])
        page = self.paginate_queryset(services.enrolment_history(student=student))
        return self.get_paginated_response(EnrolmentSerializer(page, many=True).data)


class StudentMovementListView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentMovementQuerySerializer

    @extend_schema(
        summary="Consultar movimientos del estudiante",
        description=(
            "Devuelve el historial inmutable y distingue cambios internos de seccion "
            "y traslados de ingreso o egreso."
        ),
        parameters=[StudentMovementQuerySerializer],
        responses={200: StudentMovementSerializer(many=True)},
        tags=["enrolments"],
    )
    def get(self, request):
        query = self.get_serializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        student = queries.student_or_404(query.validated_data["student_id"])
        page = self.paginate_queryset(queries.student_movements(student=student))
        return self.get_paginated_response(StudentMovementSerializer(page, many=True).data)


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
            raise AuthorizationError("Actor lacks the required permission.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        enrolment = services.matriculate_student(
            student=queries.student_or_404(payload["student_id"]),
            academic_cycle=queries.academic_cycle_or_404(payload["academic_cycle_id"]),
            grade=queries.grade_or_404(payload["grade_id"]),
            shift=queries.shift_or_404(payload["shift_id"]),
            section=queries.section_or_404(payload["section_id"]),
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
            raise AuthorizationError("Actor lacks the required permission.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        enrolment = services.reenrol_student(
            student=queries.student_or_404(payload["student_id"]),
            academic_cycle=queries.academic_cycle_or_404(payload["academic_cycle_id"]),
            grade=queries.grade_or_404(payload["grade_id"]),
            shift=queries.shift_or_404(payload["shift_id"]),
            section=queries.section_or_404(payload["section_id"]),
            effective_on=payload["effective_on"],
            actor=request.user,
        )
        return Response(MatriculationSerializer(enrolment).data, status=status.HTTP_201_CREATED)


class SectionChangeCreateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SectionChangeCreateSerializer

    @extend_schema(
        summary="Cambiar estudiante de seccion",
        description=(
            "Cierra la matricula vigente, crea su reemplazo en otra seccion del mismo "
            "ciclo y grado y conserva ambas como historial enlazado por un movimiento."
        ),
        request=SectionChangeCreateSerializer,
        responses={201: EnrolmentSerializer},
        tags=["enrolments"],
    )
    def post(self, request, enrolment_id):
        if not request.user.has_atomic_permission("enrollment_update"):
            raise AuthorizationError("Actor lacks the required permission.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        replacement = services.change_section(
            enrolment=queries.enrolment_or_404(enrolment_id),
            new_section=queries.section_or_404(payload["new_section_id"]),
            effective_on=payload["effective_on"],
            actor=request.user,
        )
        return Response(EnrolmentSerializer(replacement).data, status=status.HTTP_201_CREATED)


class StudentWithdrawalCreateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = StudentWithdrawalCreateSerializer

    @extend_schema(
        summary="Retirar estudiante",
        description=(
            "Procesa el retiro formal, cierra la matricula activa y excluye al estudiante "
            "de las listas operativas sin eliminar su historial."
        ),
        request=StudentWithdrawalCreateSerializer,
        responses={201: StudentMovementSerializer},
        tags=["enrolments"],
    )
    def post(self, request, enrolment_id):
        if not request.user.has_atomic_permission("enrollment_update"):
            raise AuthorizationError("Actor lacks the required permission.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        movement = services.withdraw_student(
            enrolment=queries.enrolment_or_404(enrolment_id),
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(StudentMovementSerializer(movement).data, status=status.HTTP_201_CREATED)


class EnrolmentDocumentRequirementListCreateView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Consultar documentos de una matricula",
        responses={200: EnrolmentDocumentRequirementSerializer(many=True)},
        tags=["enrolments"],
    )
    def get(self, request, enrolment_id):
        _ensure_enrolment_permission(request)
        enrolment = queries.enrolment_or_404(enrolment_id)
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
        enrolment = queries.enrolment_or_404(enrolment_id)
        serializer = EnrolmentDocumentRequirementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requirement = services.set_document_requirement(
            enrolment=enrolment, actor=request.user, **serializer.validated_data
        )
        return Response(EnrolmentDocumentRequirementSerializer(requirement).data)


def _ensure_enrolment_permission(request, codenames=_ENROLMENT_WRITE_PERMISSIONS):
    # Registering document state is an upsert over an existing enrolment, so both the
    # create and the update permission are legitimate. The catalogue has no read-only
    # enrolment permission yet, so the listing accepts the same pair.
    if not any(request.user.has_atomic_permission(codename) for codename in codenames):
        raise AuthorizationError("Actor lacks the required permission.")
