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

import re
import unicodedata

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.gzip import gzip_page
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import record_event
from apps.common.exceptions import AuthorizationError, DomainError, ResourceNotFoundError
from apps.evaluation import queries
from apps.evaluation.api.serializers import (
    BulkGradeResultSerializer,
    BulkGradeUploadSerializer,
    CaptureExceptionGrantSerializer,
    CaptureProgressReportSerializer,
    CloneCycleEvaluationConfigSerializer,
    CourseImportErrorsSerializer,
    CourseImportResultSerializer,
    CourseWorkbookImportSerializer,
    CycleEvaluationConfigSerializer,
    EvaluationGlobalConfigSerializer,
    EvaluationUnitSerializer,
    GradeCourseSerializer,
    GradeListFilterSerializer,
    GradeReportQuerySerializer,
    GradeReportSerializer,
    GradeSerializer,
    GradeSheetErrorsSerializer,
    GradeSheetQuerySerializer,
    GradeSheetSerializer,
    GradeSheetSubmitSerializer,
    RecoveryEligibilitySerializer,
    RecoveryGradeSerializer,
    RecoveryWindowSerializer,
    SectionRecoveryEligibilitySerializer,
)
from apps.evaluation.services import (
    assess_recovery_eligibility,
    build_capture_progress_report,
    build_course_workbook_data,
    build_grade_report,
    build_grade_sheet,
    bulk_register_unit_grades,
    clone_cycle_evaluation_config,
    close_evaluation_unit,
    create_evaluation_unit,
    get_current_average,
    get_effective_unit_count,
    get_final_subject_grade,
    get_global_evaluation_config,
    grant_capture_exception,
    import_course_grades,
    register_recovery_grade,
    register_unit_grade,
    section_recovery_eligibility,
    set_cycle_unit_count,
    set_recovery_window,
    update_global_evaluation_config,
)
from apps.evaluation.workbook import (
    XLSX_CONTENT_TYPE,
    build_course_workbook,
    read_course_workbook,
)
from apps.identity.scopes import (
    can_access_student,
    can_read_historical_student,
    historical_teaching_assignment_queryset,
    teaching_assignment_queryset,
)

EVALUATION_CONFIGURE_PERMISSION = "evaluation_configure_units"
GRADE_WRITE_PERMISSION = "grade_write"
GRADE_REPORT_PERMISSION = "grade_report"
STUDENT_VIEW_PERMISSION = "student_view_basic"

TAGS = ["evaluation: configuration"]

CONFIGURATION_DENIED = (
    "Permiso denegado: se requiere permiso y alcance para configurar la evaluación."
)
GRADE_WRITE_DENIED = "Permiso denegado: no tiene asignación docente en esta sección y curso."


def can_configure_evaluation(user, institution):
    """``evaluation.configure_units`` con alcance sobre la institución (o superusuario)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.has_scoped_permission(
        EVALUATION_CONFIGURE_PERMISSION, scope={"institution": institution}
    )


def require_evaluation_configuration(user, institution):
    if not can_configure_evaluation(user, institution):
        raise AuthorizationError(CONFIGURATION_DENIED)


def require_grade_write(request, *, unit, section, subject, **context):
    """
    ``grade.write`` con alcance sobre la sección y la subárea (RF-CAL-006): la
    asignación docente o un alcance administrativo equivalente. La denegación
    queda en la bitácora (``evaluation.grade_write_denied``).
    """
    if request.user.has_scoped_permission(
        GRADE_WRITE_PERMISSION, scope={"section": section, "subject": subject}
    ):
        return
    record_event(
        actor=request.user,
        action="evaluation.grade_write_denied",
        resource="Grade",
        context={
            "subject_id": str(subject.public_id),
            "section_id": str(section.public_id),
            "unit_id": str(unit.public_id) if unit is not None else None,
            **context,
        },
    )
    raise AuthorizationError(GRADE_WRITE_DENIED)


def can_read_enrolment_student(user, enrolment):
    """
    ``student.view_basic`` sobre el estudiante de la matrícula: alcance vigente
    (concesión, encargado o asignación docente) o el histórico del ciclo
    (RF-ALC-004). Mismo criterio que la boleta (RF-CAL-007).
    """
    return can_read_historical_student(
        user=user,
        codename=STUDENT_VIEW_PERMISSION,
        student=enrolment.student,
        academic_cycle=enrolment.academic_cycle,
        section=enrolment.section,
    ) or can_access_student(user=user, codename=STUDENT_VIEW_PERMISSION, student=enrolment.student)


def _resolve_unit(kwargs):
    unit = queries.evaluation_unit_or_none(
        cycle_public_id=kwargs.get("cycle_public_id"),
        unit_public_id=kwargs.get("unit_public_id"),
    )
    if unit is None:
        raise ResourceNotFoundError("No se encontró la unidad de evaluación.")
    return unit


def _resolve_section_subject(unit, *, section_id, subject_id):
    section = queries.section_in_cycle_or_none(
        academic_cycle=unit.academic_cycle, public_id=section_id
    )
    if section is None:
        raise ResourceNotFoundError("No se encontró la sección en el ciclo de la unidad.")
    subject = queries.subject_or_none(subject_id)
    if subject is None:
        raise ResourceNotFoundError("No se encontró la subárea.")
    return section, subject


def _bulk_response(result, *, csv_rows=False):
    """
    200 ``{created, updated}`` o 400 con ``errors``. La carga CSV conserva su
    forma de error ``{row, field, message}`` (fila 1-based) y ``created: 0``.
    """
    if not result.errors:
        return Response(
            BulkGradeResultSerializer(result).data,
            status=status.HTTP_200_OK,
        )
    if csv_rows:
        errors = [
            {"row": error["index"] + 1, "field": error["field"], "message": error["message"]}
            for error in result.errors
        ]
        return Response({"errors": errors, "created": 0}, status=status.HTTP_400_BAD_REQUEST)
    return Response({"errors": result.errors}, status=status.HTTP_400_BAD_REQUEST)


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

    def create(self, request, *args, **kwargs):
        """
        POST /api/v1/academics/cycles/{cycle_public_id}/evaluation-units/

        Creates a new evaluation unit. Requires ``evaluation.configure_units``
        over the cycle's institution. ``recovery_starts_on``/``recovery_ends_on``
        are optional: both or neither.
        """
        cycle_public_id = kwargs.get("cycle_public_id")
        if not cycle_public_id:
            raise DomainError("Se requiere cycle_public_id en la URL.")

        cycle = queries.academic_cycle_or_none(cycle_public_id)
        if cycle is None:
            raise ResourceNotFoundError("No se encontró el ciclo escolar.")

        require_evaluation_configuration(request.user, cycle.institution)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        unit = create_evaluation_unit(
            academic_cycle=cycle,
            number=data["number"],
            name=data["name"],
            starts_on=data["starts_on"],
            ends_on=data["ends_on"],
            capture_starts_on=data["capture_starts_on"],
            capture_ends_on=data["capture_ends_on"],
            recovery_starts_on=data.get("recovery_starts_on"),
            recovery_ends_on=data.get("recovery_ends_on"),
            actor=request.user,
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

    def patch(self, request, *args, **kwargs):
        unit = _resolve_unit(kwargs)
        require_evaluation_configuration(request.user, unit.academic_cycle.institution)

        serializer = RecoveryWindowSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        unit = set_recovery_window(
            unit=unit,
            recovery_starts_on=serializer.validated_data["recovery_starts_on"],
            recovery_ends_on=serializer.validated_data["recovery_ends_on"],
            actor=request.user,
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

    def patch(self, request, *args, **kwargs):
        unit = _resolve_unit(kwargs)
        require_evaluation_configuration(request.user, unit.academic_cycle.institution)

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

    def get_queryset(self):
        """Filter grants by unit and cycle from URL parameters."""
        cycle_public_id = self.kwargs.get("cycle_public_id")
        unit_public_id = self.kwargs.get("unit_public_id")
        return queries.capture_exception_grants(
            cycle_public_id=cycle_public_id, unit_public_id=unit_public_id
        )

    def list(self, request, *args, **kwargs):
        """
        GET .../capture-exceptions/

        Same permission as granting: the list carries teachers and reasons.
        """
        unit = _resolve_unit(kwargs)
        require_evaluation_configuration(request.user, unit.academic_cycle.institution)
        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """
        POST .../capture-exceptions/

        Grants a new exceptional capture authorization. Requires
        ``evaluation.configure_units`` over the unit's institution: the catalog
        has no separate permission for the exceptional gap (RF-EVC-004).
        """
        unit = _resolve_unit(kwargs)
        require_evaluation_configuration(request.user, unit.academic_cycle.institution)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        grant = grant_capture_exception(
            evaluation_unit=unit,
            subject=serializer.validated_data["subject"],
            teacher=serializer.validated_data["teacher"],
            reason=serializer.validated_data["reason"],
            expires_at=serializer.validated_data["expires_at"],
            actor=request.user,
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

    def get(self, request, *args, **kwargs):
        config = get_global_evaluation_config()
        return Response(EvaluationGlobalConfigSerializer(config).data)

    def patch(self, request, *args, **kwargs):
        # The global default belongs to the institution the system runs for.
        require_evaluation_configuration(request.user, queries.institution())

        serializer = EvaluationGlobalConfigSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        config = update_global_evaluation_config(
            default_unit_count=serializer.validated_data["default_unit_count"],
            actor=request.user,
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

    def _get_cycle_or_none(self, cycle_public_id):
        return queries.academic_cycle_or_none(cycle_public_id)

    def get(self, request, *args, **kwargs):
        cycle = self._get_cycle_or_none(kwargs.get("cycle_public_id"))
        if cycle is None:
            raise ResourceNotFoundError("No se encontró el ciclo escolar.")

        override = getattr(cycle, "evaluation_config", None)
        return Response(
            {
                "unit_count": override.unit_count if override else None,
                "effective_unit_count": get_effective_unit_count(cycle),
            }
        )

    def patch(self, request, *args, **kwargs):
        cycle = self._get_cycle_or_none(kwargs.get("cycle_public_id"))
        if cycle is None:
            raise ResourceNotFoundError("No se encontró el ciclo escolar.")

        require_evaluation_configuration(request.user, cycle.institution)

        serializer = CycleEvaluationConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        config = set_cycle_unit_count(
            academic_cycle=cycle,
            unit_count=serializer.validated_data["unit_count"],
            actor=request.user,
        )

        return Response(
            {
                "unit_count": config.unit_count,
                "effective_unit_count": get_effective_unit_count(cycle),
            },
            status=status.HTTP_200_OK,
        )


@extend_schema_view(
    post=extend_schema(
        summary="Clonar la configuracion de evaluacion hacia otro ciclo",
        description=(
            "Copia las unidades, sus ventanas de captura y recuperacion, y el "
            "override de cantidad de unidades (si existe) de este ciclo hacia "
            "``target_cycle``, con las fechas trasladadas segun la diferencia "
            "entre las fechas de inicio de ambos ciclos. El ciclo destino debe "
            "estar en preparacion y sin unidades propias; la configuracion "
            "clonada queda editable antes de activarse (RF-EVC-006)."
        ),
        tags=TAGS,
        request=CloneCycleEvaluationConfigSerializer,
        responses={201: EvaluationUnitSerializer(many=True)},
    ),
)
class CloneCycleEvaluationConfigView(APIView):
    """
    Clone a cycle's evaluation configuration into another cycle (RF-EVC-006).

    Base: /api/v1/academics/cycles/{cycle_public_id}

    POST {base}/evaluation-config/clone/
    """

    def post(self, request, *args, **kwargs):
        source_cycle = queries.academic_cycle_or_none(kwargs.get("cycle_public_id"))
        if source_cycle is None:
            raise ResourceNotFoundError("No se encontró el ciclo escolar.")

        require_evaluation_configuration(request.user, source_cycle.institution)

        serializer = CloneCycleEvaluationConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_cycle = serializer.validated_data["target_cycle"]

        units = clone_cycle_evaluation_config(
            source_cycle=source_cycle,
            target_cycle=target_cycle,
            actor=request.user,
        )

        return Response(
            EvaluationUnitSerializer(units, many=True).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(
        summary="Listar las notas de una unidad",
        description=(
            "Cada nota trae ``student`` ({public_id, student_code, full_name}), "
            "``subject_detail`` ({public_id, name}) y ``evaluation_unit_id``. Filtros "
            "opcionales por public_id: ``section_id``, ``subject_id`` y ``student_id``. "
            "Un docente solo ve las notas de sus asignaciones (RF-CAL-006)."
        ),
        tags=TAGS,
        parameters=[GradeListFilterSerializer],
    ),
    post=extend_schema(
        summary="Registrar o corregir una nota de unidad",
        description=(
            "``teacher`` es opcional: sin él se toma el docente de la asignación "
            "vigente de la sección y la subárea; si no hay, responde 400."
        ),
        tags=TAGS,
    ),
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

    GET  {base}/grades/?section_id=&subject_id=&student_id=
    POST {base}/grades/
    """

    serializer_class = GradeSerializer
    lookup_field = "public_id"

    def get_queryset(self):
        """
        Filter grades by unit and cycle from URL parameters, by the optional
        section/subject/student filters, and by the requesting teacher's own
        assignments when they are a teacher (RF-CAL-006).
        """
        filters = GradeListFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        assignments = teaching_assignment_queryset(user=self.request.user)
        return queries.grades(
            cycle_public_id=self.kwargs.get("cycle_public_id"),
            unit_public_id=self.kwargs.get("unit_public_id"),
            assignments=assignments,
            **filters.validated_data,
        )

    def create(self, request, *args, **kwargs):
        """
        POST .../grades/

        Registers (or updates) the consolidated grade for a student, subarea
        and unit. Denied, and audited as denied, if the caller has no
        assignment over the enrolment's section and the subject (RF-CAL-006).
        """
        unit = _resolve_unit(kwargs)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        enrolment = serializer.validated_data["enrolment"]
        subject = serializer.validated_data["subject"]

        require_grade_write(
            request,
            unit=unit,
            section=enrolment.section,
            subject=subject,
            enrolment_id=str(enrolment.public_id),
        )

        grade = register_unit_grade(
            enrolment=enrolment,
            subject=subject,
            evaluation_unit=unit,
            teacher=serializer.validated_data.get("teacher"),
            value=serializer.validated_data["value"],
            actor=request.user,
        )

        serializer = self.get_serializer(grade)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar el avance de captura de notas de una unidad",
        description=(
            "Por seccion y subarea del plan de estudios del ciclo: cuantas notas "
            "estan registradas, cuantas faltan y el docente responsable. "
            "``window_open`` indica si la ventana de captura sigue abierta; las "
            "filas se devuelven igual cuando ya cerro, para ver lo que quedo "
            "pendiente. Con ``evaluation.configure_units`` sobre la institución se "
            "ven todas las filas; un docente con ``grade.write`` ve solo las de sus "
            "asignaciones vigentes del ciclo. Cualquier otra cuenta recibe 403."
        ),
        tags=TAGS,
        responses={200: CaptureProgressReportSerializer},
    ),
)
class UnitCaptureProgressView(APIView):
    """
    Capture-progress panel for an evaluation unit (RF-CAL-008).

    Base: /api/v1/academics/cycles/{cycle_public_id}/evaluation-units/{unit_public_id}

    GET {base}/capture-progress/
    """

    def get(self, request, *args, **kwargs):
        unit = _resolve_unit(kwargs)

        pairs = None
        if not can_configure_evaluation(request.user, unit.academic_cycle.institution):
            if not request.user.has_atomic_permission(GRADE_WRITE_PERMISSION):
                raise AuthorizationError(CONFIGURATION_DENIED)
            pairs = queries.teacher_assignment_pairs(
                assignments=teaching_assignment_queryset(user=request.user),
                academic_cycle=unit.academic_cycle,
            )
            if not pairs:
                raise AuthorizationError(GRADE_WRITE_DENIED)

        report = build_capture_progress_report(unit, pairs=pairs)
        return Response(CaptureProgressReportSerializer(report).data)


@extend_schema_view(
    post=extend_schema(
        summary="Cargar notas de una unidad de forma masiva desde un archivo",
        description=(
            "Recibe un CSV multipart con cabecera ``student_code,value`` y los "
            "campos de formulario ``subject``, ``section`` y ``teacher`` (public "
            "IDs; ``teacher`` opcional, se toma de la asignación vigente). Valida "
            "todas las filas antes de guardar: si alguna falla no se escribe "
            "ninguna y responde 400 con ``errors`` (fila y motivo). Con todas "
            "válidas responde 200 con ``created`` (notas nuevas) y ``updated`` "
            "(notas corregidas, RF-CAL-005)."
        ),
        tags=TAGS,
        request=BulkGradeUploadSerializer,
        responses={200: BulkGradeResultSerializer, 400: dict},
    ),
)
class BulkGradeUploadView(APIView):
    """
    Bulk grade upload for an evaluation unit (RF-CAL-004).

    Base: /api/v1/academics/cycles/{cycle_public_id}/evaluation-units/{unit_public_id}

    POST {base}/grades/bulk/  (multipart/form-data)

    The 400 body here is ``{"errors": [...], "created": 0}`` -- row-level
    validation feedback the issue requires, deliberately outside the
    single-message error envelope used for rule violations.
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        unit = _resolve_unit(kwargs)

        serializer = BulkGradeUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subject = serializer.validated_data["subject"]
        section = serializer.validated_data["section"]

        # Same docente-scope check as the single-grade endpoint (RF-CAL-006).
        require_grade_write(request, unit=unit, section=section, subject=subject, bulk=True)

        result = bulk_register_unit_grades(
            evaluation_unit=unit,
            section=section,
            subject=subject,
            teacher=serializer.validated_data.get("teacher"),
            rows=serializer.validated_data["rows"],
            actor=request.user,
        )
        return _bulk_response(result, csv_rows=True)


@extend_schema_view(
    get=extend_schema(
        summary="Planilla de calificaciones de una sección y subárea",
        description=(
            "Todo lo que pinta la planilla en una llamada: la unidad (con "
            "``window_open``), la sección, la subárea, el docente de la asignación "
            "vigente (o ``null``) y una fila por matrícula activa de la sección, "
            "ordenada por apellido y nombre, con su nota o ``null`` (sin calificar). "
            "Una sola página con tope de 200 filas: una sección con más responde "
            "400. Exige ``grade.write`` sobre la sección y la subárea, o "
            "``evaluation.configure_units`` sobre la institución (solo lectura)."
        ),
        tags=TAGS,
        parameters=[GradeSheetQuerySerializer],
        responses={200: GradeSheetSerializer},
    ),
)
class GradeSheetView(APIView):
    """
    Grade sheet of an evaluation unit for one section and subarea (V2, V8).

    Base: /api/v1/academics/cycles/{cycle_public_id}/evaluation-units/{unit_public_id}

    GET {base}/sheet/?section_id=&subject_id=
    """

    def get(self, request, *args, **kwargs):
        unit = _resolve_unit(kwargs)
        params = GradeSheetQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        section, subject = _resolve_section_subject(unit, **params.validated_data)

        if not can_configure_evaluation(request.user, unit.academic_cycle.institution):
            require_grade_write(request, unit=unit, section=section, subject=subject, sheet=True)

        sheet = build_grade_sheet(evaluation_unit=unit, section=section, subject=subject)
        return Response(GradeSheetSerializer(sheet).data)


@extend_schema_view(
    post=extend_schema(
        summary="Guardar por lotes desde la planilla de calificaciones",
        description=(
            "``{section_id, subject_id, teacher_id?, grades: [{enrolment_id | "
            "student_code, value}]}`` (hasta 200). Mismas reglas que la carga CSV: "
            "todo o nada; 200 ``{created, updated}`` o 400 ``{errors: [{index, "
            "student_code, field, message}]}``. Una nota existente se corrige por "
            "la misma vía que una corrección individual (RF-CAL-005): ventana de "
            "captura abierta o brecha vigente, y bitácora con valor anterior y "
            "nuevo. Exige ``grade.write`` sobre la sección y la subárea."
        ),
        tags=TAGS,
        request=GradeSheetSubmitSerializer,
        responses={200: BulkGradeResultSerializer, 400: GradeSheetErrorsSerializer},
    ),
)
class GradeSheetSaveView(APIView):
    """
    Batch save from the grade sheet (V2). Shares bulk_register_unit_grades
    with the CSV upload.

    POST {base}/grades/sheet/
    """

    def post(self, request, *args, **kwargs):
        unit = _resolve_unit(kwargs)
        serializer = GradeSheetSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        section = data["section_id"]
        subject = data["subject_id"]

        require_grade_write(request, unit=unit, section=section, subject=subject, sheet=True)

        result = bulk_register_unit_grades(
            evaluation_unit=unit,
            section=section,
            subject=subject,
            teacher=data.get("teacher_id"),
            rows=data["grades"],
            actor=request.user,
        )
        return _bulk_response(result)


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
        raise ResourceNotFoundError("No se encontró la matrícula.")

    subject = queries.subject_or_none(subject_id)
    if subject is None:
        raise ResourceNotFoundError("No se encontró el curso.")

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
        summary="Consultar la elegibilidad de recuperacion de un estudiante",
        description=(
            "Evalua en conjunto tres condiciones: asistencia del ciclo de al menos "
            "80%, cantidad de subareas reprobadas dentro del limite del plan de "
            "estudios (3 si el plan tiene 9 subareas o menos, 4 si tiene mas), y que "
            "el estudiante no haya usado ya su oportunidad de recuperacion en el ciclo. "
            "Exige ``student.view_basic`` sobre el estudiante (mismo criterio que la "
            "boleta)."
        ),
        tags=TAGS,
        responses={200: RecoveryEligibilitySerializer},
    ),
)
class RecoveryEligibilityView(APIView):
    """
    Recovery eligibility for a student's enrolment (RF-RES-004).

    Base: /api/v1/academics/cycles/{cycle_public_id}

    GET {base}/enrolments/{enrolment_id}/recovery-eligibility/
    """

    def get(self, request, *args, **kwargs):
        enrolment = queries.enrolment_or_none(
            cycle_public_id=kwargs.get("cycle_public_id"),
            enrolment_id=kwargs.get("enrolment_id"),
        )
        if enrolment is None:
            raise ResourceNotFoundError("No se encontró la matrícula.")

        if not can_read_enrolment_student(request.user, enrolment):
            raise AuthorizationError(
                "Permiso denegado: no hay una asociación vigente con este estudiante."
            )

        eligibility = assess_recovery_eligibility(enrolment)
        return Response(RecoveryEligibilitySerializer(eligibility).data)


@extend_schema_view(
    post=extend_schema(
        summary="Registrar la nota de recuperacion de una subarea",
        description=(
            "Solo para estudiantes declarados elegibles (RF-RES-004), sobre una "
            "subarea en condicion reprobada y con la ventana de recuperacion del "
            "ciclo abierta. La nota de recuperacion se conserva junto a la nota "
            "final original sin sustituirla; la condicion de la subarea se "
            "recalcula a partir de la recuperacion. Exige ``grade.write`` sobre la "
            "sección de la matrícula y la subárea."
        ),
        tags=TAGS,
        request=RecoveryGradeSerializer,
        responses={201: RecoveryGradeSerializer},
    ),
)
class RecoveryGradeCreateView(APIView):
    """
    Register a recovery grade for a failed subarea (RF-RES-005).

    Base: /api/v1/academics/cycles/{cycle_public_id}

    POST {base}/enrolments/{enrolment_id}/recovery-grades/
    """

    def post(self, request, *args, **kwargs):
        enrolment = queries.enrolment_or_none(
            cycle_public_id=kwargs.get("cycle_public_id"),
            enrolment_id=kwargs.get("enrolment_id"),
        )
        if enrolment is None:
            raise ResourceNotFoundError("No se encontró la matrícula.")

        serializer = RecoveryGradeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # The subarea's teacher records its recovery, like any other grade.
        require_grade_write(
            request,
            unit=None,
            section=enrolment.section,
            subject=serializer.validated_data["subject"],
            enrolment_id=str(enrolment.public_id),
            recovery=True,
        )

        recovery = register_recovery_grade(
            enrolment=enrolment,
            subject=serializer.validated_data["subject"],
            value=serializer.validated_data["value"],
            actor=request.user,
        )
        # Recompute the subarea condition off the freshly stored recovery so the
        # response carries what get_final_subject_grade now reports.
        recovery.recovery_condition = get_final_subject_grade(
            enrolment, serializer.validated_data["subject"]
        )["condition"]

        return Response(
            RecoveryGradeSerializer(recovery).data,
            status=status.HTTP_201_CREATED,
        )


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
            raise ResourceNotFoundError("No se encontró la matrícula.")

        if not can_read_enrolment_student(request.user, enrolment):
            raise AuthorizationError(
                "Permiso denegado: no hay una asociación vigente con este estudiante."
            )

        grades = queries.grades_for_enrolment(enrolment)
        return Response(GradeSerializer(grades, many=True).data)


@extend_schema_view(
    get=extend_schema(
        summary="Elegibilidad de recuperación de una sección",
        description=(
            "Paginado (``page``, ``page_size``), por apellido y nombre del estudiante. "
            "Una fila por matrícula activa de la sección con ``eligible``, "
            "``reasons`` y las subáreas reprobadas (``failed_subjects``: "
            "[{public_id, name, final_grade}]). Reutiliza la misma evaluación que el "
            "endpoint por matrícula. Exige ``student.view_basic`` con alcance sobre "
            "la sección."
        ),
        tags=TAGS,
        responses={200: SectionRecoveryEligibilitySerializer(many=True)},
    ),
)
class SectionRecoveryEligibilityView(ListAPIView):
    """
    Recovery eligibility of every active enrolment of a section (V4).

    Base: /api/v1/academics/cycles/{cycle_public_id}

    GET {base}/sections/{section_id}/recovery-eligibility/

    Cost: assess_recovery_eligibility per enrolment of the page (attendance
    plus the final grade of each subarea of the plan), so it is bounded by
    the page size (25 by default, 100 at most), not by the section.
    """

    serializer_class = SectionRecoveryEligibilitySerializer

    def get_queryset(self):
        cycle = queries.academic_cycle_or_none(self.kwargs.get("cycle_public_id"))
        if cycle is None:
            raise ResourceNotFoundError("No se encontró el ciclo escolar.")
        section = queries.section_in_cycle_or_none(
            academic_cycle=cycle, public_id=self.kwargs.get("section_id")
        )
        if section is None:
            raise ResourceNotFoundError("No se encontró la sección en el ciclo.")
        if not self.request.user.has_scoped_permission(
            STUDENT_VIEW_PERMISSION, scope={"section": section}
        ):
            raise AuthorizationError(
                "Permiso denegado: se requiere permiso y alcance sobre la sección."
            )
        return queries.active_section_enrolments(section)

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        rows = section_recovery_eligibility(page)
        return self.get_paginated_response(self.get_serializer(rows, many=True).data)


# --------------------------------------------------------------------------- #
# Cursos del docente, plantilla Excel por curso e informe de calificaciones
# --------------------------------------------------------------------------- #


def _resolve_cycle(kwargs):
    cycle = queries.academic_cycle_or_none(kwargs.get("cycle_public_id"))
    if cycle is None:
        raise ResourceNotFoundError("No se encontró el ciclo escolar.")
    return cycle


def _resolve_course(cycle, *, section_id, subject_id):
    section = queries.section_in_cycle_or_none(academic_cycle=cycle, public_id=section_id)
    if section is None:
        raise ResourceNotFoundError("No se encontró la sección en el ciclo.")
    subject = queries.subject_or_none(subject_id)
    if subject is None:
        raise ResourceNotFoundError("No se encontró la subárea.")
    return section, subject


def _grades_institution_wide(user, institution):
    """
    Whether the account works on every course of the institution: superuser,
    ``grade.write`` with institutional scope (dirección, secretaría) or
    evaluation configuration (read-only sheet). A teacher's ``grade.write`` is
    scoped to their teaching assignments and does not match an institution.
    """
    return (
        user.is_superuser
        or user.has_scoped_permission(GRADE_WRITE_PERMISSION, scope={"institution": institution})
        or can_configure_evaluation(user, institution)
    )


def _course_label(section):
    offering = section.offering
    label = f"{offering.grade.name} {section.name}"
    return f"{label} · {offering.shift.name}" if offering.shift_id else label


@extend_schema_view(
    get=extend_schema(
        summary="Cursos que la cuenta puede calificar en un ciclo",
        description=(
            "Una fila por curso (sección y subárea), sin paginar: el total está acotado "
            "por secciones × plan de estudios. Dirección y secretaría (``grade.write`` "
            "institucional o configuración de evaluación) ven todos los cursos del plan; "
            "un docente ve solo los de sus asignaciones vigentes en el ciclo (o, en un "
            "ciclo cerrado, las que tuvo). Quien no califica recibe una lista vacía."
        ),
        tags=TAGS,
        responses={200: GradeCourseSerializer(many=True)},
    )
)
class GradeCoursesView(APIView):
    """
    GET /api/v1/academics/cycles/{cycle_public_id}/grade-courses/
    """

    def get(self, request, *args, **kwargs):
        cycle = _resolve_cycle(kwargs)
        institution = cycle.institution
        if _grades_institution_wide(request.user, institution):
            pairs = queries.cycle_course_pairs(cycle)
        elif request.user.has_atomic_permission(GRADE_WRITE_PERMISSION):
            assignments = (
                teaching_assignment_queryset(user=request.user)
                if cycle.status == cycle.CycleStatus.ACTIVE
                else historical_teaching_assignment_queryset(
                    user=request.user, academic_cycle=cycle
                )
            )
            pairs = queries.assignment_course_pairs(assignments, cycle)
        else:
            pairs = []
        teachers = queries.current_teachers_by_pair(cycle) if pairs else {}
        rows = []
        for section, subject in pairs:
            teacher = teachers.get((section.pk, subject.pk))
            rows.append(
                {
                    "section": {
                        "public_id": section.public_id,
                        "label": _course_label(section),
                        "grade_name": section.offering.grade.name,
                    },
                    "subject": {"public_id": subject.public_id, "name": subject.name},
                    "teacher_name": (
                        f"{teacher.first_name} {teacher.last_name}".strip() if teacher else None
                    ),
                }
            )
        return Response(GradeCourseSerializer(rows, many=True).data)


@extend_schema_view(
    get=extend_schema(
        summary="Plantilla Excel de notas de un curso",
        description=(
            "Archivo .xlsx con una fila por matrícula activa de la sección (código y "
            "nombre bloqueados), una columna por unidad activa del ciclo con las notas "
            "registradas, validación de 0 a 100 y columnas grises en las unidades que "
            "hoy no admiten captura. Exige ``grade.write`` sobre la sección y la "
            "subárea, o configuración de evaluación institucional."
        ),
        tags=TAGS,
        parameters=[GradeSheetQuerySerializer],
        responses={(200, XLSX_CONTENT_TYPE): bytes},
    )
)
class CourseWorkbookView(APIView):
    """
    GET /api/v1/academics/cycles/{cycle_public_id}/grade-workbook/?section_id=&subject_id=
    """

    def get(self, request, *args, **kwargs):
        cycle = _resolve_cycle(kwargs)
        params = GradeSheetQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        section, subject = _resolve_course(cycle, **params.validated_data)
        if not can_configure_evaluation(request.user, cycle.institution):
            require_grade_write(request, unit=None, section=section, subject=subject, workbook=True)

        data = build_course_workbook_data(
            academic_cycle=cycle,
            section=section,
            subject=subject,
            institution=cycle.institution,
        )
        filename = _workbook_filename(subject.name, data["section_label"])
        response = HttpResponse(build_course_workbook(data), content_type=XLSX_CONTENT_TYPE)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


def _workbook_filename(subject_name, section_label):
    raw = f"notas-{subject_name}-{section_label}".lower()
    ascii_only = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_only).strip("-")
    return f"{slug or 'notas'}.xlsx"


@extend_schema_view(
    post=extend_schema(
        summary="Importar la plantilla Excel de notas de un curso",
        description=(
            "Multipart ``{file, section_id, subject_id}``. Identifica a cada estudiante "
            "por su código, nunca por el nombre. Todo o nada: 200 ``{created, updated, "
            "unchanged}`` o 400 ``{errors: [{row, student_code, unit, message}]}`` con la "
            "fila de Excel. Una celda vacía no cambia nada y una igual a la nota "
            "registrada se ignora; una nota nueva o distinta exige que la unidad admita "
            "captura hoy (ventana, cierre y permisos excepcionales). Escribe con un "
            "número fijo de consultas y audita cada nota. Exige ``grade.write`` sobre la "
            "sección y la subárea."
        ),
        tags=TAGS,
        request={"multipart/form-data": CourseWorkbookImportSerializer},
        responses={200: CourseImportResultSerializer, 400: CourseImportErrorsSerializer},
    )
)
class CourseWorkbookImportView(APIView):
    """
    POST /api/v1/academics/cycles/{cycle_public_id}/grade-workbook/import/
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        cycle = _resolve_cycle(kwargs)
        serializer = CourseWorkbookImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        section, subject = _resolve_course(
            cycle, section_id=payload["section_id"], subject_id=payload["subject_id"]
        )
        require_grade_write(request, unit=None, section=section, subject=subject, workbook=True)

        workbook = read_course_workbook(payload["file"])
        result = import_course_grades(
            academic_cycle=cycle,
            section=section,
            subject=subject,
            workbook=workbook,
            actor=request.user,
        )
        if result.errors:
            return Response({"errors": result.errors}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CourseImportResultSerializer(result).data)


def require_grade_report(request, cycle, filters):
    """``grade.report`` con alcance institucional (dirección y secretaría) o superusuario."""
    user = request.user
    if user.is_superuser or user.has_scoped_permission(
        GRADE_REPORT_PERMISSION, scope={"institution": cycle.institution}
    ):
        return
    record_event(
        actor=user,
        action="evaluation.grade_report_denied",
        resource="Grade",
        context={"cycle_id": str(cycle.public_id), **filters},
    )
    raise AuthorizationError("Permiso denegado: se requiere el permiso para imprimir notas.")


@extend_schema_view(
    get=extend_schema(
        summary="Datos del informe de calificaciones",
        description=(
            "Todo el ciclo, un grado (``grade_id``), una sección de ese grado "
            "(``section_id``) o un estudiante (``student_id``). Por estudiante: una fila "
            "por subárea del plan de su grado con la nota de cada unidad activa, el "
            "promedio del curso, el promedio de cada unidad y el promedio general. "
            "Los promedios excluyen las unidades sin nota y redondean al entero, mitad "
            "hacia arriba. El navegador arma el PDF; el servidor solo calcula. "
            "Respuesta comprimida con gzip. Exige ``grade.report`` institucional y "
            "queda en la bitácora."
        ),
        tags=TAGS,
        parameters=[GradeReportQuerySerializer],
        responses={200: GradeReportSerializer},
    )
)
@method_decorator(gzip_page, name="dispatch")
class GradeReportView(APIView):
    """
    GET /api/v1/academics/cycles/{cycle_public_id}/grade-report/
    """

    def get(self, request, *args, **kwargs):
        cycle = _resolve_cycle(kwargs)
        params = GradeReportQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        filters = {key: str(value) for key, value in params.validated_data.items()}
        require_grade_report(request, cycle, filters)

        grade = section = student = None
        if params.validated_data.get("grade_id"):
            grade = queries.grade_in_institution_or_none(
                institution=cycle.institution, public_id=params.validated_data["grade_id"]
            )
            if grade is None:
                raise ResourceNotFoundError("No se encontró el grado.")
        if params.validated_data.get("section_id"):
            section = queries.section_in_cycle_or_none(
                academic_cycle=cycle, public_id=params.validated_data["section_id"]
            )
            if section is None or section.offering.grade_id != grade.pk:
                raise ResourceNotFoundError("No se encontró la sección en ese grado y ciclo.")
        if params.validated_data.get("student_id"):
            student = queries.student_or_none(params.validated_data["student_id"])
            if student is None:
                raise ResourceNotFoundError("No se encontró el estudiante.")

        report = build_grade_report(
            academic_cycle=cycle,
            institution=cycle.institution,
            grade=grade,
            section=section,
            student=student,
            actor=request.user,
        )
        # Diccionario ya plano (enteros, textos, UUID y fechas): pasarlo por los
        # serializadores anidados costaba cientos de milisegundos con cientos de
        # estudiantes y no agregaba nada. GradeReportSerializer documenta la forma.
        return Response(report)
