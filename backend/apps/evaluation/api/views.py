"""
API views for evaluation domain.

RF-EVC-001: Estructura de unidades del ciclo
RF-EVC-002: Ventana de captura de notas
RF-EVC-003: Ventana de recuperacion
RF-EVC-004: Brecha excepcional autorizada
RF-EVC-005: Configuracion global heredable

Authorization: requires role=director + permission=evaluation.configure_units

Las vistas de configuracion son ``APIView`` sin ``serializer_class``, asi que
drf-spectacular no puede adivinar su contrato y las descartaba por completo: no
aparecian en el schema publicado. Cada operacion lo declara con
``extend_schema``.
"""

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_event
from apps.common.exceptions import AuthorizationError, DomainError, ResourceNotFoundError
from apps.evaluation import queries
from apps.evaluation.api.serializers import (
    CaptureExceptionGrantSerializer,
    CycleEvaluationConfigSerializer,
    EvaluationGlobalConfigSerializer,
    EvaluationUnitSerializer,
    GradeSerializer,
    RecoveryWindowSerializer,
)
from apps.evaluation.services import (
    close_evaluation_unit,
    create_evaluation_unit,
    get_current_average,
    get_effective_unit_count,
    get_final_subject_grade,
    get_global_evaluation_config,
    grant_capture_exception,
    register_unit_grade,
    set_cycle_unit_count,
    set_recovery_window,
    update_global_evaluation_config,
)
from apps.identity.scopes import can_access_student, teaching_assignment_queryset

STUDENT_VIEW_PERMISSION = "student_view_basic"

TAGS = ["evaluation: configuration"]


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
        return queries.evaluation_units(self.kwargs.get("cycle_public_id"))

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
            raise DomainError("Se requiere cycle_public_id en la URL.")

        if not self.check_director_permission():
            raise AuthorizationError(
                "Permission denied. Only directors can configure evaluation units."
            )

        cycle = queries.academic_cycle_or_none(cycle_public_id)
        if cycle is None:
            raise ResourceNotFoundError("Cycle not found.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        unit = create_evaluation_unit(
            academic_cycle=cycle,
            number=serializer.validated_data["number"],
            name=serializer.validated_data["name"],
            starts_on=serializer.validated_data["starts_on"],
            ends_on=serializer.validated_data["ends_on"],
            capture_starts_on=serializer.validated_data["capture_starts_on"],
            capture_ends_on=serializer.validated_data["capture_ends_on"],
        )

        serializer = self.get_serializer(unit)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    patch=extend_schema(
        summary="Configurar la ventana de recuperacion de una unidad",
        description="La fecha de fin no puede ser anterior a la de inicio.",
        tags=TAGS,
        request=RecoveryWindowSerializer,
        responses={200: EvaluationUnitSerializer},
    ),
)
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
            raise AuthorizationError(
                "Permission denied. Only directors can configure evaluation units."
            )

        cycle_public_id = kwargs.get("cycle_public_id")
        unit_public_id = kwargs.get("unit_public_id")

        unit = queries.evaluation_unit_or_none(
            cycle_public_id=cycle_public_id, unit_public_id=unit_public_id
        )
        if unit is None:
            raise ResourceNotFoundError("Evaluation unit not found.")

        serializer = RecoveryWindowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        unit = set_recovery_window(
            unit=unit,
            recovery_starts_on=serializer.validated_data["recovery_starts_on"],
            recovery_ends_on=serializer.validated_data["recovery_ends_on"],
        )

        return Response(
            EvaluationUnitSerializer(unit).data,
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    patch=extend_schema(
        summary="Cerrar una unidad de evaluacion",
        description=(
            "Una unidad cerrada deja de admitir captura o correccion de notas salvo "
            "brecha excepcional vigente (RF-EVC-007)."
        ),
        tags=TAGS,
        request=None,
        responses={200: EvaluationUnitSerializer},
    ),
)
class EvaluationUnitCloseView(APIView):
    """
    Close an evaluation unit (RF-EVC-007).

    Base: /api/v1/academics/cycles/{cycle_public_id}/evaluation-units/{unit_public_id}

    PATCH {base}/close/
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
            raise AuthorizationError(
                "Permission denied. Only directors can configure evaluation units."
            )

        cycle_public_id = kwargs.get("cycle_public_id")
        unit_public_id = kwargs.get("unit_public_id")

        unit = queries.evaluation_unit_or_none(
            cycle_public_id=cycle_public_id, unit_public_id=unit_public_id
        )
        if unit is None:
            raise ResourceNotFoundError("Evaluation unit not found.")

        unit = close_evaluation_unit(unit, actor=request.user)

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
        return queries.capture_exception_grants(
            cycle_public_id=cycle_public_id, unit_public_id=unit_public_id
        )

    def create(self, request, *args, **kwargs):
        """
        POST .../capture-exceptions/

        Grants a new exceptional capture authorization. Only users with
        academic authorization permission can grant one.
        """
        if not self.check_director_permission():
            raise AuthorizationError(
                "Permission denied. Only academic authorization can grant capture exceptions."
            )

        cycle_public_id = kwargs.get("cycle_public_id")
        unit_public_id = kwargs.get("unit_public_id")

        unit = queries.evaluation_unit_or_none(
            cycle_public_id=cycle_public_id, unit_public_id=unit_public_id
        )
        if unit is None:
            raise ResourceNotFoundError("Evaluation unit not found.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        grant = grant_capture_exception(
            evaluation_unit=unit,
            subject=serializer.validated_data["subject"],
            teacher=serializer.validated_data["teacher"],
            reason=serializer.validated_data["reason"],
            expires_at=serializer.validated_data["expires_at"],
        )

        serializer = self.get_serializer(grant)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar la configuracion institucional de evaluacion",
        tags=TAGS,
        responses={200: EvaluationGlobalConfigSerializer},
    ),
    patch=extend_schema(
        summary="Actualizar la configuracion institucional de evaluacion",
        description="Solo afecta a los ciclos que no tengan configuracion propia.",
        tags=TAGS,
        request=EvaluationGlobalConfigSerializer,
        responses={200: EvaluationGlobalConfigSerializer},
    ),
)
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
            raise AuthorizationError(
                "Permission denied. Only directors can configure evaluation settings."
            )

        serializer = EvaluationGlobalConfigSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        config = update_global_evaluation_config(
            default_unit_count=serializer.validated_data["default_unit_count"],
        )

        return Response(EvaluationGlobalConfigSerializer(config).data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar la configuracion de evaluacion de un ciclo",
        description="Un ciclo sin configuracion propia hereda el default institucional.",
        tags=TAGS,
        responses={200: CycleEvaluationConfigSerializer},
    ),
    patch=extend_schema(
        summary="Definir la configuracion de evaluacion de un ciclo",
        description=(
            "Sobrescribe el default institucional solo para este ciclo; no cambia la "
            "configuracion global ni la de ningun otro ciclo."
        ),
        tags=TAGS,
        request=CycleEvaluationConfigSerializer,
        responses={200: CycleEvaluationConfigSerializer},
    ),
)
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
        return queries.academic_cycle_or_none(cycle_public_id)

    def get(self, request, *args, **kwargs):
        cycle = self._get_cycle_or_none(kwargs.get("cycle_public_id"))
        if cycle is None:
            raise ResourceNotFoundError("Cycle not found.")

        override = getattr(cycle, "evaluation_config", None)
        return Response(
            {
                "unit_count": override.unit_count if override else None,
                "effective_unit_count": get_effective_unit_count(cycle),
            }
        )

    def patch(self, request, *args, **kwargs):
        if not self.check_director_permission():
            raise AuthorizationError(
                "Permission denied. Only directors can configure evaluation settings."
            )

        cycle = self._get_cycle_or_none(kwargs.get("cycle_public_id"))
        if cycle is None:
            raise ResourceNotFoundError("Cycle not found.")

        serializer = CycleEvaluationConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        config = set_cycle_unit_count(
            academic_cycle=cycle,
            unit_count=serializer.validated_data["unit_count"],
        )

        return Response(
            {
                "unit_count": config.unit_count,
                "effective_unit_count": get_effective_unit_count(cycle),
            },
            status=status.HTTP_200_OK,
        )


class GradeListCreateView(ListAPIView, CreateAPIView):
    """
    List and register unit grades for an evaluation unit (RF-CAL-001).

    RF-CAL-006: a teacher may only write, or list, grades for a section and
    subject they are formally assigned to (via TeachingAssignment) in the
    current cycle. An actor with no teaching assignment at all (e.g. a
    director acting through an administrative scope grant) is not filtered
    on read; scope enforcement on read only kicks in for actual teachers.

    Base: /api/v1/academics/cycles/{cycle_public_id}/evaluation-units/{unit_public_id}

    GET  {base}/grades/
    POST {base}/grades/
    """

    serializer_class = GradeSerializer
    lookup_field = "public_id"

    def check_teacher_permission(self):
        """Verify the caller is authenticated; scope is checked separately."""
        return bool(self.request.user and self.request.user.is_authenticated)

    def get_queryset(self):
        """
        Filter grades by unit and cycle from URL parameters, and further by
        the requesting teacher's own assignments when they are a teacher
        (RF-CAL-006).
        """
        cycle_public_id = self.kwargs.get("cycle_public_id")
        unit_public_id = self.kwargs.get("unit_public_id")
        assignments = teaching_assignment_queryset(user=self.request.user)
        return queries.grades(
            cycle_public_id=cycle_public_id,
            unit_public_id=unit_public_id,
            assignments=assignments,
        )

    def create(self, request, *args, **kwargs):
        """
        POST .../grades/

        Registers (or updates) the consolidated grade for a student, subarea
        and unit. Denied, and audited as denied, if the caller has no
        assignment over the enrolment's section and the subject (RF-CAL-006).
        """
        if not self.check_teacher_permission():
            raise AuthorizationError("Permission denied. Only teachers can register grades.")

        cycle_public_id = kwargs.get("cycle_public_id")
        unit_public_id = kwargs.get("unit_public_id")

        unit = queries.evaluation_unit_or_none(
            cycle_public_id=cycle_public_id, unit_public_id=unit_public_id
        )
        if unit is None:
            raise ResourceNotFoundError("Evaluation unit not found.")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        enrolment = serializer.validated_data["enrolment"]
        subject = serializer.validated_data["subject"]

        if not request.user.has_scoped_permission(
            "grade_write", scope={"section": enrolment.section, "subject": subject}
        ):
            record_event(
                actor=request.user,
                action="evaluation.grade_write_denied",
                resource="Grade",
                context={
                    "enrolment_id": str(enrolment.public_id),
                    "subject_id": str(subject.public_id),
                    "unit_id": str(unit.public_id),
                },
            )
            raise AuthorizationError(
                "Permission denied. No teaching assignment over this section and subject."
            )

        grade = register_unit_grade(
            enrolment=enrolment,
            subject=subject,
            evaluation_unit=unit,
            teacher=serializer.validated_data["teacher"],
            value=serializer.validated_data["value"],
            actor=request.user,
        )

        serializer = self.get_serializer(grade)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


def _resolve_enrolment_subject(cycle_public_id, enrolment_id, subject_id):
    """
    Resolve (enrolment, subject) for the current-average and final-grade
    endpoints, both keyed the same way. Raises a domain-level not-found error
    which the central API exception handler serializes consistently.
    """
    enrolment = queries.enrolment_or_none(
        cycle_public_id=cycle_public_id, enrolment_id=enrolment_id
    )
    if enrolment is None:
        raise ResourceNotFoundError("Enrolment not found.")

    subject = queries.subject_or_none(subject_id)
    if subject is None:
        raise ResourceNotFoundError("Subject not found.")

    return enrolment, subject


@extend_schema_view(
    get=extend_schema(
        summary="Consultar el promedio en curso de un estudiante en una subarea",
        description=(
            "Promedia unicamente las unidades con nota registrada. Una unidad sin "
            "nota nunca se trata como cero: se cuenta como pendiente."
        ),
        tags=TAGS,
        responses={200: dict},
    ),
)
class CurrentAverageView(APIView):
    """
    Running average of a student's grades for a subarea (RF-CAL-003).

    Base: /api/v1/academics/cycles/{cycle_public_id}

    GET {base}/enrolments/{enrolment_id}/subjects/{subject_id}/current-average/
    """

    def get(self, request, *args, **kwargs):
        enrolment, subject = _resolve_enrolment_subject(
            kwargs.get("cycle_public_id"), kwargs.get("enrolment_id"), kwargs.get("subject_id")
        )

        return Response(get_current_average(enrolment, subject))


@extend_schema_view(
    get=extend_schema(
        summary="Consultar la nota final de un estudiante en una subarea",
        description=(
            "Promedio de las notas de unidad de la subarea. Mientras el ciclo esta "
            "abierto, se recalcula ante cualquier correccion."
        ),
        tags=TAGS,
        responses={200: dict},
    ),
)
class FinalSubjectGradeView(APIView):
    """
    Final grade of a student's subarea for the cycle (RF-RES-001).

    Base: /api/v1/academics/cycles/{cycle_public_id}

    GET {base}/enrolments/{enrolment_id}/subjects/{subject_id}/final-grade/
    """

    def get(self, request, *args, **kwargs):
        enrolment, subject = _resolve_enrolment_subject(
            kwargs.get("cycle_public_id"), kwargs.get("enrolment_id"), kwargs.get("subject_id")
        )

        return Response(get_final_subject_grade(enrolment, subject))


@extend_schema_view(
    get=extend_schema(
        summary="Consultar las notas de un estudiante (portal de encargado)",
        description=(
            "Devuelve unicamente las notas del estudiante de la matricula indicada. "
            "El sistema nunca expone listados comparativos de la seccion (RF-CAL-007)."
        ),
        tags=TAGS,
        responses={200: GradeSerializer(many=True)},
    ),
)
class EnrolmentGradesView(APIView):
    """
    All registered grades for one enrolment, scoped to the caller's own
    associations (RF-CAL-007).

    A guardian sees only the students with a current association
    (guardian_student_queryset, via authorized_student_queryset); anyone
    without an effective scope over this student is denied.

    Base: /api/v1/academics/cycles/{cycle_public_id}

    GET {base}/enrolments/{enrolment_id}/grades/
    """

    def get(self, request, *args, **kwargs):
        cycle_public_id = kwargs.get("cycle_public_id")
        enrolment_id = kwargs.get("enrolment_id")

        enrolment = queries.enrolment_or_none(
            cycle_public_id=cycle_public_id, enrolment_id=enrolment_id
        )
        if enrolment is None:
            raise ResourceNotFoundError("Enrolment not found.")

        if not can_access_student(
            user=request.user, codename=STUDENT_VIEW_PERMISSION, student=enrolment.student
        ):
            raise AuthorizationError(
                "Permission denied. No hay una asociacion vigente con este estudiante."
            )

        grades = queries.grades_for_enrolment(enrolment)
        return Response(GradeSerializer(grades, many=True).data)
