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

from collections import defaultdict

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.academics import queries, services
from apps.common.api.caching import CacheableListMixin
from apps.common.exceptions import AuthorizationError, DomainError, ResourceNotFoundError
from apps.common.listing import descending_too, search_and_order
from apps.evaluation import queries as evaluation_queries
from apps.teachers import queries as teacher_queries

from .serializers import (
    AcademicCycleCloneSerializer,
    AcademicCycleCreateSerializer,
    AcademicCycleDefaultsSerializer,
    AcademicCycleReadinessSerializer,
    AcademicCycleReopenSerializer,
    AcademicCycleRevertSerializer,
    AcademicCycleSerializer,
    AcademicCycleUpdateSerializer,
    AssignmentMatrixRowSerializer,
    CampusCreateSerializer,
    CampusSerializer,
    CampusUpdateSerializer,
    ClassroomCreateSerializer,
    ClassroomSerializer,
    ClassroomUpdateSerializer,
    ClassScheduleBlockCreateSerializer,
    ClassScheduleBlockSerializer,
    ClassScheduleBlockUpdateSerializer,
    ClassScheduleCloneSerializer,
    ClassSchedulePublicationSerializer,
    ClassSessionCreateSerializer,
    ClassSessionSerializer,
    CloneAssignmentPreviewSerializer,
    CurriculumPlanCreateSerializer,
    CurriculumPlanSerializer,
    CurriculumPlanUpdateSerializer,
    FrozenPromotionResultSerializer,
    FrozenSubjectResultCorrectionSerializer,
    FrozenSubjectResultSerializer,
    GradeCreateSerializer,
    GradeSerializer,
    GradeUpdateSerializer,
    HistoricalAcademicCycleSerializer,
    LevelCreateSerializer,
    LevelSerializer,
    LevelSubjectCreateSerializer,
    LevelSubjectSerializer,
    LevelSubjectUpdateSerializer,
    LevelUpdateSerializer,
    LevelWithGradesSerializer,
    NonComputableDayCreateSerializer,
    NonComputableDaySerializer,
    SectionCreateSerializer,
    SectionSerializer,
    SectionUpdateSerializer,
    ShiftCreateSerializer,
    ShiftSerializer,
    ShiftUpdateSerializer,
    SubjectCreateSerializer,
    SubjectSerializer,
    SubjectUpdateSerializer,
    SuggestedCodeSerializer,
    TeachingAssignmentBatchResultSerializer,
    TeachingAssignmentBatchSerializer,
    TeachingAssignmentCreateSerializer,
    TeachingAssignmentReassignSerializer,
    TeachingAssignmentSerializer,
    WeeklyLoadRowSerializer,
)

CATALOGUE = ["academics: catalogue"]
CYCLES = ["academics: cycles"]

# Los catalogos editables (sedes, jornadas, niveles, cursos, secciones) se
# revalidan siempre: con ETag y 304 el navegador no vuelve a descargar un
# listado que no cambio, pero tampoco sirve uno viejo sin preguntar. Antes era
# max-age=300 y un curso recien creado tardaba hasta 5 minutos en verse
# (docs/ux-ui.md 1.2.1, A1, N1).
CATALOGUE_CACHE_SECONDS = 0

SEARCH = OpenApiParameter(
    name="search",
    type=str,
    location=OpenApiParameter.QUERY,
    required=False,
    description="Texto a buscar (sin distinguir mayúsculas) en nombre y código.",
)


def ordering_parameter(orderings):
    return OpenApiParameter(
        name="ordering",
        type=str,
        location=OpenApiParameter.QUERY,
        required=False,
        enum=sorted(orderings),
        description="Orden del listado. Un valor no admitido conserva el orden por omisión.",
    )


NAME_CODE_SEARCH = ("name", "code")
NAME_CODE_ORDERINGS = descending_too({"name": ("name",), "code": ("code",)})
SEQUENCE_ORDERINGS = descending_too(
    {"sequence": ("sequence", "name"), "name": ("name",), "code": ("code",)}
)
CLASSROOM_ORDERINGS = descending_too(
    {
        "name": ("name",),
        "code": ("code",),
        "campus": ("campus__name", "name"),
        "capacity": ("capacity", "name"),
    }
)
# Las secciones no tienen codigo: se buscan por su nombre y el de su grado.
SECTION_SEARCH = ("name", "offering__grade__name", "offering__grade__code")
SECTION_ORDERINGS = descending_too(
    {
        "grade": ("offering__grade__level__sequence", "offering__grade__sequence", "name"),
        "name": ("name",),
        "shift": ("offering__shift__name", "name"),
        "capacity": ("capacity", "name"),
    }
)
# Una entrada del plan se reconoce por su curso y su grado.
CURRICULUM_PLAN_SEARCH = ("subject__name", "subject__code", "grade__name", "grade__code")
CURRICULUM_PLAN_ORDERINGS = descending_too(
    {
        "subject": ("subject__name",),
        "grade": ("grade__level__sequence", "grade__sequence", "subject__name"),
    }
)

INCLUDE_INACTIVE = OpenApiParameter(
    name="include_inactive",
    type=bool,
    location=OpenApiParameter.QUERY,
    required=False,
    description="Incluye registros desactivados. Por defecto solo se listan los activos.",
)

YEAR = OpenApiParameter(
    name="year",
    type=int,
    location=OpenApiParameter.QUERY,
    required=False,
    description="Anio del ciclo. Por omision, el proximo respecto al ciclo mas reciente.",
)


def _include_inactive(request):
    return str(request.query_params.get("include_inactive", "")).lower() in {"1", "true", "yes"}


def positional(payload, resolve):
    """
    Translate ``insert_after`` from the payload into what the service expects.

    Three states, and they mean different things: absent is "no position given"
    (append), an explicit ``null`` is the FIRST position, and an identifier is
    the sibling to follow. Collapsing absent and null would silently move a
    rename to the top of the list.
    """
    if "insert_after" not in payload:
        return {}
    reference = payload.pop("insert_after")
    return {"insert_after": None if reference is None else resolve(reference)}


# --------------------------------------------------------------------------- #
# base classes
# --------------------------------------------------------------------------- #


class CatalogueView(GenericAPIView):
    """Authenticated access plus the institution the request operates on."""

    permission_classes = [permissions.IsAuthenticated]

    @property
    def institution(self):
        if not hasattr(self, "_institution"):
            self._institution = queries.resolve_institution()
        return self._institution

    def validated(self, serializer_class, request):
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def require_assignment_scope(self):
        if not self.request.user.has_scoped_permission(
            "scope_assign", scope={"institution": self.institution}
        ):
            raise AuthorizationError(
                "El actor no tiene el permiso requerido o el alcance sobre la institución."
            )

    def require_revert_scope(self):
        # Mismo razonamiento que require_reopen_scope: alcance de institucion,
        # sin "academic_cycle" en el alcance (D6, RF-CIC-008).
        if not self.request.user.has_scoped_permission(
            "academic_cycle_revert", scope={"institution": self.institution}
        ):
            raise AuthorizationError(
                "El actor no tiene el permiso requerido o el alcance sobre la institución."
            )

    def require_reopen_scope(self):
        # No "academic_cycle" key in the scope: scope_matches() would deny a
        # closed cycle outright for any write-permission codename before the
        # grant is even checked (identity/scopes.py), which is exactly what
        # RF-CIC-005 needs to authorize. Institution alone is enough — same
        # granularity as require_assignment_scope.
        if not self.request.user.has_scoped_permission(
            "academic_cycle_reopen", scope={"institution": self.institution}
        ):
            raise AuthorizationError(
                "El actor no tiene el permiso requerido o el alcance sobre la institución."
            )


class CatalogueListCreateView(CatalogueView):
    """
    ``GET`` lists a queryset, paginated; ``POST`` delegates to a service.

    Subclasses provide ``list_serializer``, ``create_serializer``,
    ``list_queryset(request, **kwargs)`` and ``create(request, payload, **kwargs)``.
    """

    list_serializer = None
    create_serializer = None
    # `search` y `ordering` (api-conventions.md): cada listado declara en que
    # campos se busca y que ordenes admite; apps.common.listing los aplica.
    search_fields = ()
    orderings = {}

    def get_serializer_class(self):
        if self.request.method == "POST":
            return self.create_serializer
        return self.list_serializer

    def listing(self, request, **kwargs):
        return search_and_order(
            self.list_queryset(request, **kwargs),
            search=request.query_params.get("search"),
            ordering=request.query_params.get("ordering"),
            search_fields=self.search_fields,
            orderings=self.orderings,
        )

    def get(self, request, **kwargs):
        page = self.paginate_queryset(self.listing(request, **kwargs))
        return self.get_paginated_response(self.list_serializer(page, many=True).data)

    def post(self, request, **kwargs):
        self.require_assignment_scope()
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
        self.require_assignment_scope()
        payload = self.validated(self.update_serializer, request)
        self.update(request, self.get_object(**kwargs), payload)
        return self.represent(self.get_object(**kwargs))


class DeactivateMixin:
    def delete(self, request, **kwargs):
        self.require_assignment_scope()
        self.deactivate(request, self.get_object(**kwargs))
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------- #
# academic cycles
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar ciclos escolares",
        tags=["academics: cycles"],
        responses={200: AcademicCycleSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Registrar ciclo escolar",
        tags=["academics: cycles"],
        request=AcademicCycleCreateSerializer,
        responses={201: AcademicCycleSerializer},
    ),
)
class AcademicCycleListCreateView(CacheableListMixin, CatalogueListCreateView):
    list_serializer = AcademicCycleSerializer
    create_serializer = AcademicCycleCreateSerializer
    # Siempre revalidar (ETag + 304), nunca servir de cache sin preguntar: crear,
    # activar o cerrar un ciclo cambia este listado, y con max-age de 5 minutos
    # el navegador devolvia el listado viejo al recargar tras la mutacion.
    cache_seconds = 0

    def list_queryset(self, request):
        return queries.academic_cycles(self.institution)

    def create(self, request, payload):
        return services.create_academic_cycle(
            institution=self.institution,
            actor=request.user,
            **payload,
        )


class HistoricalAcademicCycleDetailView(CatalogueView):
    serializer_class = HistoricalAcademicCycleSerializer

    @extend_schema(
        summary="Consultar detalle historico de un ciclo escolar",
        description=(
            "Devuelve estructura, planes, asignaciones docentes y resumen agregado de matriculas. "
            "Incluye registros inactivos para conservar la historia institucional."
        ),
        tags=["academics: cycles"],
        responses={200: HistoricalAcademicCycleSerializer},
    )
    def get(self, request, public_id):
        cycle = queries.historical_cycle_or_404(self.institution, public_id)
        return Response(self.get_serializer(cycle).data)

    @extend_schema(
        summary="Editar ciclo escolar en preparación",
        description=(
            "C3: corrige año, nombre, descripción y vigencia de un ciclo en borrador. "
            "Mismas reglas que al crearlo (año igual al de la fecha de inicio, nombre y año "
            "únicos, sin traslape). Un ciclo activo o cerrado se rechaza con 400."
        ),
        tags=CYCLES,
        request=AcademicCycleUpdateSerializer,
        responses={200: AcademicCycleSerializer},
    )
    def patch(self, request, public_id):
        self.require_assignment_scope()
        payload = self.validated(AcademicCycleUpdateSerializer, request)
        cycle = queries.academic_cycle_or_404(self.institution, public_id)
        updated = services.update_academic_cycle(cycle=cycle, actor=request.user, **payload)
        return Response(AcademicCycleSerializer(updated).data)


class AcademicCycleActivateView(CatalogueView):
    @extend_schema(
        summary="Activar ciclo escolar",
        tags=["academics: cycles"],
        request=None,
        responses={200: AcademicCycleSerializer},
    )
    def post(self, request, public_id):
        self.require_assignment_scope()
        cycle = queries.academic_cycle_or_404(self.institution, public_id)
        activated = services.activate_academic_cycle(cycle=cycle, actor=request.user)
        return Response(AcademicCycleSerializer(activated).data)


class AcademicCycleCloseView(CatalogueView):
    @extend_schema(
        summary="Cerrar ciclo escolar",
        description=(
            "Cierra un ciclo activo. Exige que todas sus unidades de evaluacion esten "
            "cerradas y que la ventana de recuperacion, si existe, ya haya vencido."
        ),
        tags=["academics: cycles"],
        request=None,
        responses={200: AcademicCycleSerializer},
    )
    def post(self, request, public_id):
        self.require_assignment_scope()
        cycle = queries.academic_cycle_or_404(self.institution, public_id)
        closed = services.close_academic_cycle(cycle=cycle, actor=request.user)
        return Response(AcademicCycleSerializer(closed).data)


class AcademicCycleReopenView(CatalogueView):
    @extend_schema(
        summary="Reabrir ciclo escolar cerrado",
        description=(
            "Reapertura excepcional de un ciclo cerrado. Requiere el permiso "
            "academic_cycle_reopen sobre la institucion y un motivo obligatorio; "
            "ambos quedan en la bitacora."
        ),
        tags=["academics: cycles"],
        request=AcademicCycleReopenSerializer,
        responses={200: AcademicCycleSerializer},
    )
    def post(self, request, public_id):
        self.require_reopen_scope()
        payload = self.validated(AcademicCycleReopenSerializer, request)
        cycle = queries.academic_cycle_or_404(self.institution, public_id)
        reopened = services.reopen_academic_cycle(
            cycle=cycle, reason=payload["reason"], actor=request.user
        )
        return Response(AcademicCycleSerializer(reopened).data)


class AcademicCycleRevertToDraftView(CatalogueView):
    @extend_schema(
        summary="Volver a borrador un ciclo activo",
        description=(
            "D3/D6 (RF-CIC-008): devuelve a borrador un ciclo activado por error. Exige el "
            "permiso academic_cycle_revert sobre la institución y un motivo obligatorio. Se "
            "rechaza si el ciclo ya tiene matrículas, notas, movimientos de asistencia, "
            "unidades de evaluación cerradas o documentos emitidos. Conserva estructura y "
            "asignaciones docentes."
        ),
        tags=CYCLES,
        request=AcademicCycleRevertSerializer,
        responses={200: AcademicCycleSerializer},
    )
    def post(self, request, public_id):
        self.require_revert_scope()
        payload = self.validated(AcademicCycleRevertSerializer, request)
        cycle = queries.academic_cycle_or_404(self.institution, public_id)
        reverted = services.revert_academic_cycle_to_draft(
            academic_cycle=cycle, reason=payload["reason"], actor=request.user
        )
        return Response(AcademicCycleSerializer(reverted).data)


class AcademicCycleReadinessView(CatalogueView):
    serializer_class = AcademicCycleReadinessSerializer

    @extend_schema(
        summary="Consultar qué permite hoy el ciclo",
        description=(
            "C7/D1/D6: lista de verificación para activar, bloqueos para volver a borrador, "
            "pendientes para cerrar y el otro ciclo activo de la institución, si existe."
        ),
        tags=CYCLES,
        responses={200: AcademicCycleReadinessSerializer},
    )
    def get(self, request, public_id):
        cycle = queries.academic_cycle_or_404(self.institution, public_id)
        readiness = queries.academic_cycle_readiness(cycle)
        return Response(AcademicCycleReadinessSerializer(readiness).data)


@extend_schema_view(
    get=extend_schema(
        summary="Listar días no computables del ciclo",
        description="RF-JOR-010: días excluidos del cálculo de asistencia, ordenados por fecha.",
        tags=CYCLES,
        responses={200: NonComputableDaySerializer(many=True)},
    ),
    post=extend_schema(
        summary="Declarar día no computable",
        description="RF-JOR-010: la fecha debe caer dentro de la vigencia del ciclo.",
        tags=CYCLES,
        request=NonComputableDayCreateSerializer,
        responses={201: NonComputableDaySerializer},
    ),
)
class CycleNonComputableDayListCreateView(CatalogueListCreateView):
    list_serializer = NonComputableDaySerializer
    create_serializer = NonComputableDayCreateSerializer

    def list_queryset(self, request, public_id):
        cycle = queries.academic_cycle_or_404(self.institution, public_id)
        return queries.non_computable_days(cycle)

    def create(self, request, payload, public_id):
        cycle = queries.academic_cycle_or_404(self.institution, public_id)
        return services.declare_non_computable_day(
            academic_cycle=cycle, day=payload["day"], reason=payload["reason"], actor=request.user
        )


class NonComputableDayDetailView(CatalogueView):
    @extend_schema(
        summary="Quitar día no computable",
        description=(
            "RF-JOR-010: el día vuelve a contar para asistencia. Se desactiva (no se borra) y "
            "queda en la bitácora. Se rechaza si el ciclo está cerrado."
        ),
        tags=CYCLES,
        responses={204: None},
    )
    def delete(self, request, public_id):
        self.require_assignment_scope()
        record = queries.non_computable_day_or_404(self.institution, public_id)
        services.remove_non_computable_day(record=record, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AcademicCycleCloneView(CatalogueView):
    serializer_class = AcademicCycleCloneSerializer

    @extend_schema(
        summary="Clonar estructura hacia un ciclo nuevo",
        tags=["academics: cycles"],
        request=AcademicCycleCloneSerializer,
        responses={201: AcademicCycleSerializer},
    )
    def post(self, request, public_id):
        self.require_assignment_scope()
        source = queries.academic_cycle_or_404(self.institution, public_id)
        payload = self.validated(AcademicCycleCloneSerializer, request)
        cloned = services.clone_academic_cycle(
            source_cycle=source,
            actor=request.user,
            **payload,
        )
        return Response(AcademicCycleSerializer(cloned).data, status=status.HTTP_201_CREATED)


# --------------------------------------------------------------------------- #
# campuses ("sedes")
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar sedes",
        description="Sedes de la institucion. Solo activas salvo `include_inactive=true`.",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE, SEARCH, ordering_parameter(NAME_CODE_ORDERINGS)],
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
class CampusListCreateView(CacheableListMixin, CatalogueListCreateView):
    list_serializer = CampusSerializer
    create_serializer = CampusCreateSerializer
    cache_seconds = CATALOGUE_CACHE_SECONDS
    search_fields = NAME_CODE_SEARCH
    orderings = NAME_CODE_ORDERINGS

    def list_queryset(self, request):
        return queries.campuses(self.institution, include_inactive=_include_inactive(request))

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
# classrooms ("aulas")
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar aulas",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE, SEARCH, ordering_parameter(CLASSROOM_ORDERINGS)],
        responses={200: ClassroomSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Registrar aula",
        tags=CATALOGUE,
        request=ClassroomCreateSerializer,
        responses={201: ClassroomSerializer},
    ),
)
class ClassroomListCreateView(CatalogueListCreateView):
    list_serializer = ClassroomSerializer
    create_serializer = ClassroomCreateSerializer
    search_fields = NAME_CODE_SEARCH
    orderings = CLASSROOM_ORDERINGS

    def list_queryset(self, request):
        return queries.classrooms(
            self.institution,
            include_inactive=_include_inactive(request),
            campus_id=request.query_params.get("campus_id"),
        )

    def create(self, request, payload):
        campus = queries.campus_or_404(self.institution, payload.pop("campus_id"))
        return services.create_classroom(campus=campus, actor=request.user, **payload)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar aula", tags=CATALOGUE, responses={200: ClassroomSerializer}
    ),
    patch=extend_schema(
        summary="Actualizar aula",
        tags=CATALOGUE,
        request=ClassroomUpdateSerializer,
        responses={200: ClassroomSerializer},
    ),
    delete=extend_schema(summary="Desactivar aula", tags=CATALOGUE, responses={204: None}),
)
class ClassroomDetailView(RetrieveMixin, UpdateMixin, DeactivateMixin, CatalogueDetailView):
    detail_serializer = ClassroomSerializer
    update_serializer = ClassroomUpdateSerializer

    def get_object(self, public_id):
        return queries.classroom_or_404(self.institution, public_id)

    def update(self, request, classroom, payload):
        services.update_classroom(classroom=classroom, actor=request.user, **payload)

    def deactivate(self, request, classroom):
        services.deactivate_classroom(classroom=classroom, actor=request.user)


# --------------------------------------------------------------------------- #
# shifts ("jornadas") — always under a campus
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar jornadas de una sede",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE, SEARCH, ordering_parameter(NAME_CODE_ORDERINGS)],
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
class CampusShiftListCreateView(CacheableListMixin, CatalogueListCreateView):
    list_serializer = ShiftSerializer
    create_serializer = ShiftCreateSerializer
    cache_seconds = CATALOGUE_CACHE_SECONDS
    search_fields = NAME_CODE_SEARCH
    orderings = NAME_CODE_ORDERINGS

    def list_queryset(self, request, public_id):
        return queries.shifts(
            queries.campus_or_404(self.institution, public_id),
            include_inactive=_include_inactive(request),
        )

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


# --------------------------------------------------------------------------- #
# schedule blocks ("rejilla de bloques") -- RF-HOR-001
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar bloques de la rejilla horaria",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE],
        responses={200: ClassScheduleBlockSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Registrar bloque de la rejilla horaria",
        description="Se rechaza si el bloque se solapa con otro ya registrado en la jornada.",
        tags=CATALOGUE,
        request=ClassScheduleBlockCreateSerializer,
        responses={201: ClassScheduleBlockSerializer},
    ),
)
class ShiftClassScheduleBlockListCreateView(CatalogueListCreateView):
    list_serializer = ClassScheduleBlockSerializer
    create_serializer = ClassScheduleBlockCreateSerializer

    def list_queryset(self, request, public_id):
        return queries.class_schedule_blocks(
            queries.shift_or_404(self.institution, public_id),
            include_inactive=_include_inactive(request),
        )

    def create(self, request, payload, public_id):
        shift = queries.shift_or_404(self.institution, public_id)
        return services.create_class_schedule_block(shift=shift, actor=request.user, **payload)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar bloque de la rejilla horaria",
        tags=CATALOGUE,
        responses={200: ClassScheduleBlockSerializer},
    ),
    patch=extend_schema(
        summary="Actualizar bloque de la rejilla horaria",
        description="Renombra y/o reprograma el bloque. Numero y jornada son inmutables.",
        tags=CATALOGUE,
        request=ClassScheduleBlockUpdateSerializer,
        responses={200: ClassScheduleBlockSerializer},
    ),
    delete=extend_schema(
        summary="Desactivar bloque de la rejilla horaria",
        tags=CATALOGUE,
        responses={204: None},
    ),
)
class ClassScheduleBlockDetailView(
    RetrieveMixin, UpdateMixin, DeactivateMixin, CatalogueDetailView
):
    detail_serializer = ClassScheduleBlockSerializer
    update_serializer = ClassScheduleBlockUpdateSerializer

    def get_object(self, public_id):
        return queries.class_schedule_block_or_404(self.institution, public_id)

    def update(self, request, block, payload):
        services.update_class_schedule_block(block=block, actor=request.user, **payload)

    def deactivate(self, request, block):
        services.deactivate_class_schedule_block(block=block, actor=request.user)


# --------------------------------------------------------------------------- #
# levels ("niveles")
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar niveles",
        description="Niveles ordenados por su secuencia pedagogica.",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE, SEARCH, ordering_parameter(SEQUENCE_ORDERINGS)],
        responses={200: LevelSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Crear nivel",
        description=(
            "Registra un nivel educativo (preprimaria, primaria, basico, diversificado). "
            "`sequence` define el orden pedagogico y es unico por institucion."
        ),
        tags=CATALOGUE,
        request=LevelCreateSerializer,
        responses={201: LevelSerializer},
    ),
)
class LevelListCreateView(CacheableListMixin, CatalogueListCreateView):
    list_serializer = LevelSerializer
    create_serializer = LevelCreateSerializer
    cache_seconds = CATALOGUE_CACHE_SECONDS
    search_fields = NAME_CODE_SEARCH
    orderings = SEQUENCE_ORDERINGS

    def list_queryset(self, request):
        return queries.levels(self.institution, include_inactive=_include_inactive(request))

    def get(self, request, **kwargs):
        # `?expand=grades` existe para el selector de "Presencia en tiempo
        # real": sin el, listar niveles con sus grados costaba una peticion
        # por nivel (N+1). Es angosto a proposito -- un solo campo, un solo
        # call site -- en vez de un mecanismo generico de expand que nadie mas
        # necesita todavia.
        if request.query_params.get("expand") != "grades":
            return super().get(request, **kwargs)

        levels = list(self.listing(request, **kwargs))
        page = self.paginate_queryset(levels)

        grades_by_level = defaultdict(list)
        for grade in queries.grades_for_levels(page, include_inactive=_include_inactive(request)):
            grades_by_level[grade.level_id].append(grade)
        for level in page:
            level._expanded_grades = grades_by_level[level.id]

        return self.get_paginated_response(LevelWithGradesSerializer(page, many=True).data)

    def create(self, request, payload):
        payload.update(positional(payload, self._sibling))
        level = services.create_level(institution=self.institution, actor=request.user, **payload)
        return queries.level_or_404(self.institution, level.public_id)

    def _sibling(self, public_id):
        return queries.level_or_404(self.institution, public_id)


@extend_schema_view(
    get=extend_schema(summary="Consultar nivel", tags=CATALOGUE, responses={200: LevelSerializer}),
    patch=extend_schema(
        summary="Actualizar nivel",
        tags=CATALOGUE,
        request=LevelUpdateSerializer,
        responses={200: LevelSerializer},
    ),
    delete=extend_schema(
        summary="Desactivar nivel",
        description="Desactiva el nivel y sus grados. Se rechaza si un ciclo abierto los oferta.",
        tags=CATALOGUE,
        responses={204: None},
    ),
)
class LevelDetailView(RetrieveMixin, UpdateMixin, DeactivateMixin, CatalogueDetailView):
    detail_serializer = LevelSerializer
    update_serializer = LevelUpdateSerializer

    def get_object(self, public_id):
        return queries.level_or_404(self.institution, public_id)

    def update(self, request, level, payload):
        payload.update(positional(payload, self._sibling))
        services.update_level(level=level, actor=request.user, **payload)

    def deactivate(self, request, level):
        services.deactivate_level(level=level, actor=request.user)

    def _sibling(self, public_id):
        return queries.level_or_404(self.institution, public_id)


# --------------------------------------------------------------------------- #
# grades ("grados") — always under a level
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar grados de un nivel",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE, SEARCH, ordering_parameter(SEQUENCE_ORDERINGS)],
        responses={200: GradeSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Crear grado en un nivel",
        description="El codigo del grado es unico en toda la institucion.",
        tags=CATALOGUE,
        request=GradeCreateSerializer,
        responses={201: GradeSerializer},
    ),
)
class LevelGradeListCreateView(CatalogueListCreateView):
    list_serializer = GradeSerializer
    create_serializer = GradeCreateSerializer
    search_fields = NAME_CODE_SEARCH
    orderings = SEQUENCE_ORDERINGS

    def list_queryset(self, request, public_id):
        return queries.grades(
            queries.level_or_404(self.institution, public_id),
            include_inactive=_include_inactive(request),
        )

    def create(self, request, payload, public_id):
        level = queries.level_or_404(self.institution, public_id)
        payload.update(positional(payload, lambda pid: queries.grade_or_404(self.institution, pid)))
        return services.create_grade(level=level, actor=request.user, **payload)


@extend_schema_view(
    get=extend_schema(summary="Consultar grado", tags=CATALOGUE, responses={200: GradeSerializer}),
    patch=extend_schema(
        summary="Actualizar grado",
        tags=CATALOGUE,
        request=GradeUpdateSerializer,
        responses={200: GradeSerializer},
    ),
    delete=extend_schema(
        summary="Desactivar grado",
        description="Se rechaza si el grado esta ofertado en un ciclo no cerrado.",
        tags=CATALOGUE,
        responses={204: None},
    ),
)
class GradeDetailView(RetrieveMixin, UpdateMixin, DeactivateMixin, CatalogueDetailView):
    detail_serializer = GradeSerializer
    update_serializer = GradeUpdateSerializer

    def get_object(self, public_id):
        return queries.grade_or_404(self.institution, public_id)

    def update(self, request, grade, payload):
        payload.update(positional(payload, lambda pid: queries.grade_or_404(self.institution, pid)))
        services.update_grade(grade=grade, actor=request.user, **payload)

    def deactivate(self, request, grade):
        services.deactivate_grade(grade=grade, actor=request.user)


# --------------------------------------------------------------------------- #
# subjects ("cursos")
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar cursos",
        description="Cursos de la institucion, con los niveles en los que se imparten.",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE, SEARCH, ordering_parameter(NAME_CODE_ORDERINGS)],
        responses={200: SubjectSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Crear curso",
        tags=CATALOGUE,
        request=SubjectCreateSerializer,
        responses={201: SubjectSerializer},
    ),
)
class SubjectListCreateView(CacheableListMixin, CatalogueListCreateView):
    list_serializer = SubjectSerializer
    create_serializer = SubjectCreateSerializer
    cache_seconds = CATALOGUE_CACHE_SECONDS
    search_fields = NAME_CODE_SEARCH
    orderings = NAME_CODE_ORDERINGS

    def list_queryset(self, request):
        return queries.subjects(self.institution, include_inactive=_include_inactive(request))

    def create(self, request, payload):
        return services.create_subject(institution=self.institution, actor=request.user, **payload)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar curso", tags=CATALOGUE, responses={200: SubjectSerializer}
    ),
    patch=extend_schema(
        summary="Actualizar curso",
        tags=CATALOGUE,
        request=SubjectUpdateSerializer,
        responses={200: SubjectSerializer},
    ),
    delete=extend_schema(
        summary="Desactivar curso",
        description="Los vinculos con niveles se conservan como historia.",
        tags=CATALOGUE,
        responses={204: None},
    ),
)
class SubjectDetailView(RetrieveMixin, UpdateMixin, DeactivateMixin, CatalogueDetailView):
    detail_serializer = SubjectSerializer
    update_serializer = SubjectUpdateSerializer

    def get_object(self, public_id):
        return queries.subject_or_404(self.institution, public_id)

    def update(self, request, subject, payload):
        services.update_subject(subject=subject, actor=request.user, **payload)

    def deactivate(self, request, subject):
        services.deactivate_subject(subject=subject, actor=request.user)


# --------------------------------------------------------------------------- #
# level <-> subject links
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar cursos de un nivel",
        description="Cursos vinculados al nivel, con obligatoriedad y carga horaria.",
        tags=CATALOGUE,
        responses={200: LevelSubjectSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Vincular curso a un nivel",
        description=(
            "Declara que un curso se imparte en el nivel. Nivel y curso deben pertenecer "
            "a la misma institucion. `weekly_hours=0` significa sin definir."
        ),
        tags=CATALOGUE,
        request=LevelSubjectCreateSerializer,
        responses={201: LevelSubjectSerializer},
    ),
)
class LevelSubjectListCreateView(CatalogueListCreateView):
    list_serializer = LevelSubjectSerializer
    create_serializer = LevelSubjectCreateSerializer

    def list_queryset(self, request, public_id):
        return queries.level_subjects(queries.level_or_404(self.institution, public_id))

    def create(self, request, payload, public_id):
        level = queries.level_or_404(self.institution, public_id)
        subject = _resolve_subject(payload.pop("subject_id"))
        return services.link_subject_to_level(
            level=level, subject=subject, actor=request.user, **payload
        )


@extend_schema_view(
    patch=extend_schema(
        summary="Actualizar el vinculo curso-nivel",
        tags=CATALOGUE,
        request=LevelSubjectUpdateSerializer,
        responses={200: LevelSubjectSerializer},
    ),
    delete=extend_schema(
        summary="Desvincular curso de un nivel",
        tags=CATALOGUE,
        responses={204: None},
    ),
)
class LevelSubjectDetailView(UpdateMixin, DeactivateMixin, CatalogueDetailView):
    """
    Addressed by the (level, subject) pair, but the resource is the link itself,
    so ``get_object`` resolves straight to it. An unlinked pair raises a
    ``DomainError`` and lands as a 400, not a 404: both ends exist.
    """

    detail_serializer = LevelSubjectSerializer
    update_serializer = LevelSubjectUpdateSerializer

    def get_object(self, public_id, subject_public_id):
        return services.get_level_subject(
            queries.level_or_404(self.institution, public_id),
            queries.subject_or_404(self.institution, subject_public_id),
        )

    def update(self, request, link, payload):
        services.update_level_subject(
            level=link.level, subject=link.subject, actor=request.user, **payload
        )

    def deactivate(self, request, link):
        services.unlink_subject_from_level(
            level=link.level, subject=link.subject, actor=request.user
        )


# --------------------------------------------------------------------------- #
# sections ("secciones")
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar secciones",
        description=(
            "Secciones de la institucion. Filtra opcionalmente por ciclo (`academic_cycle_id`) "
            "y grado (`grade_id`). Solo activas salvo `include_inactive=true`."
        ),
        tags=CATALOGUE,
        parameters=[
            INCLUDE_INACTIVE,
            SEARCH,
            ordering_parameter(SECTION_ORDERINGS),
            OpenApiParameter("academic_cycle_id", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("grade_id", str, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: SectionSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Crear seccion",
        description=(
            "Registra una seccion dentro de la oferta (ciclo, grado, jornada) indicada. "
            "La oferta se resuelve o se crea automaticamente si todavia no existia."
        ),
        tags=CATALOGUE,
        request=SectionCreateSerializer,
        responses={201: SectionSerializer},
    ),
)
class SectionListCreateView(CacheableListMixin, CatalogueListCreateView):
    list_serializer = SectionSerializer
    create_serializer = SectionCreateSerializer
    cache_seconds = CATALOGUE_CACHE_SECONDS
    search_fields = SECTION_SEARCH
    orderings = SECTION_ORDERINGS

    def list_queryset(self, request):
        return queries.sections(
            self.institution,
            include_inactive=_include_inactive(request),
            academic_cycle_id=request.query_params.get("academic_cycle_id"),
            grade_id=request.query_params.get("grade_id"),
        )

    def create(self, request, payload):
        academic_cycle = queries.academic_cycle_or_404(
            self.institution, payload["academic_cycle_id"]
        )
        grade = queries.grade_for_payload(self.institution, payload["grade_id"])
        shift = queries.shift_for_payload(self.institution, payload["shift_id"])
        default_classroom = (
            queries.classroom_or_404(self.institution, payload["default_classroom_id"])
            if payload.get("default_classroom_id")
            else None
        )
        section = services.create_section(
            academic_cycle=academic_cycle,
            grade=grade,
            shift=shift,
            name=payload["name"],
            capacity=payload.get("capacity", 0),
            default_classroom=default_classroom,
            actor=request.user,
        )
        return queries.section_or_404(self.institution, section.public_id)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar seccion", tags=CATALOGUE, responses={200: SectionSerializer}
    ),
    patch=extend_schema(
        summary="Actualizar seccion",
        tags=CATALOGUE,
        request=SectionUpdateSerializer,
        responses={200: SectionSerializer},
    ),
    delete=extend_schema(
        summary="Desactivar seccion",
        description=(
            "Desactiva la seccion en lugar de eliminarla. Se rechaza si tiene matriculas "
            "activas o si el ciclo ya esta cerrado."
        ),
        tags=CATALOGUE,
        responses={204: None},
    ),
)
class SectionDetailView(RetrieveMixin, UpdateMixin, DeactivateMixin, CatalogueDetailView):
    detail_serializer = SectionSerializer
    update_serializer = SectionUpdateSerializer

    def get_object(self, public_id):
        return queries.section_or_404(self.institution, public_id)

    def update(self, request, section, payload):
        default_classroom_id = payload.pop("default_classroom_id", None)
        default_classroom = (
            queries.classroom_or_404(self.institution, default_classroom_id)
            if default_classroom_id
            else None
        )
        services.update_section(
            section=section, default_classroom=default_classroom, actor=request.user, **payload
        )

    def deactivate(self, request, section):
        services.deactivate_section(section=section, actor=request.user)


# --------------------------------------------------------------------------- #
# class sessions ("sesiones de clase") -- RF-HOR-003
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar sesiones de clase de una seccion",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE],
        responses={200: ClassSessionSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Agendar sesion de clase",
        description=(
            "El bloque de horario debe pertenecer a la misma jornada que la seccion. "
            "El docente se deriva de la asignacion vigente (RF-HOR-004), no se captura aqui."
        ),
        tags=CATALOGUE,
        request=ClassSessionCreateSerializer,
        responses={201: ClassSessionSerializer},
    ),
)
class SectionClassSessionListCreateView(CatalogueListCreateView):
    list_serializer = ClassSessionSerializer
    create_serializer = ClassSessionCreateSerializer

    def list_queryset(self, request, public_id):
        return queries.class_sessions(
            queries.section_or_404(self.institution, public_id),
            include_inactive=_include_inactive(request),
        )

    def create(self, request, payload, public_id):
        section = queries.section_or_404(self.institution, public_id)
        subject = queries.subject_for_payload(payload["subject_id"])
        schedule_block = queries.class_schedule_block_for_payload(
            self.institution, payload["schedule_block_id"]
        )
        classroom = (
            queries.classroom_or_404(self.institution, payload["classroom_id"])
            if payload.get("classroom_id")
            else None
        )
        return services.create_class_session(
            academic_cycle=section.academic_cycle,
            section=section,
            subject=subject,
            schedule_block=schedule_block,
            day_of_week=payload["day_of_week"],
            classroom=classroom,
            starts_on=payload.get("starts_on"),
            actor=request.user,
        )


class SectionClassScheduleCloneView(CatalogueView):
    serializer_class = ClassScheduleCloneSerializer

    @extend_schema(
        summary="Clonar horario hacia una seccion",
        description=(
            "Copia atomicamente las sesiones activas de la seccion origen hacia la seccion "
            "destino. Traduce los bloques por numero y no copia aulas ni docentes."
        ),
        tags=CATALOGUE,
        request=ClassScheduleCloneSerializer,
        responses={201: ClassSessionSerializer(many=True)},
    )
    def post(self, request, public_id):
        self.require_assignment_scope()
        payload = self.validated(ClassScheduleCloneSerializer, request)
        target_section = queries.section_or_404(self.institution, public_id)
        source_section = queries.section_or_404(
            self.institution,
            payload["source_section_id"],
        )
        sessions = services.clone_class_schedule(
            source_section=source_section,
            target_section=target_section,
            actor=request.user,
        )
        return Response(
            ClassSessionSerializer(sessions, many=True).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    get=extend_schema(
        summary="Consultar sesion de clase", tags=CATALOGUE, responses={200: ClassSessionSerializer}
    ),
    delete=extend_schema(
        summary="Desactivar sesion de clase",
        tags=CATALOGUE,
        responses={204: None},
    ),
)
class ClassSessionDetailView(RetrieveMixin, DeactivateMixin, CatalogueDetailView):
    detail_serializer = ClassSessionSerializer

    def get_object(self, public_id):
        return queries.class_session_or_404(self.institution, public_id)

    def deactivate(self, request, session):
        services.deactivate_class_session(session=session, actor=request.user)


class SectionWeeklyLoadView(CatalogueView):
    @extend_schema(
        summary="Verificar carga horaria semanal de la seccion",
        description=(
            "RF-HOR-007. Por cada subarea del plan de estudios del grado, compara "
            "las horas semanales declaradas (LevelSubject, RF-EST-006) contra los "
            "periodos activos realmente agendados para esta seccion. Una subarea "
            "sin horas declaradas a nivel de nivel educativo devuelve "
            "declared_weekly_hours y matches en null: no hay con que comparar."
        ),
        tags=CATALOGUE,
        responses={200: WeeklyLoadRowSerializer(many=True)},
    )
    def get(self, request, public_id):
        section = queries.section_or_404(self.institution, public_id)
        rows = queries.weekly_load_report(section)
        return Response(WeeklyLoadRowSerializer(rows, many=True).data)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar estado de publicacion del horario",
        tags=CATALOGUE,
        responses={200: ClassSchedulePublicationSerializer},
    ),
    post=extend_schema(
        summary="Publicar el horario del ciclo",
        tags=CATALOGUE,
        request=None,
        responses={200: ClassSchedulePublicationSerializer},
    ),
    delete=extend_schema(
        summary="Despublicar el horario del ciclo (volver a borrador)",
        tags=CATALOGUE,
        responses={200: ClassSchedulePublicationSerializer},
    ),
)
class ClassSchedulePublicationView(CatalogueView):
    """RF-HOR-009: publicar/despublicar el horario. Sin filtrado por rol (RF-HOR-010, #203)."""

    def get(self, request, public_id):
        cycle = queries.academic_cycle_or_404(self.institution, public_id)
        publication = queries.class_schedule_publication(cycle)
        return Response(ClassSchedulePublicationSerializer(publication).data)

    def post(self, request, public_id):
        self.require_assignment_scope()
        cycle = queries.academic_cycle_or_404(self.institution, public_id)
        publication = services.publish_class_schedule(academic_cycle=cycle, actor=request.user)
        return Response(ClassSchedulePublicationSerializer(publication).data)

    def delete(self, request, public_id):
        self.require_assignment_scope()
        cycle = queries.academic_cycle_or_404(self.institution, public_id)
        publication = services.unpublish_class_schedule(academic_cycle=cycle, actor=request.user)
        return Response(ClassSchedulePublicationSerializer(publication).data)


# --------------------------------------------------------------------------- #
# curriculum plans ("plan de estudios")
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar plan de estudios",
        description=(
            "Asignaciones de curso a grado por ciclo. Filtra opcionalmente por ciclo "
            "(`academic_cycle_id`) y grado (`grade_id`). Solo activas salvo "
            "`include_inactive=true`."
        ),
        tags=CATALOGUE,
        parameters=[
            INCLUDE_INACTIVE,
            SEARCH,
            ordering_parameter(CURRICULUM_PLAN_ORDERINGS),
            OpenApiParameter("academic_cycle_id", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("grade_id", str, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: CurriculumPlanSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Agregar curso al plan de estudios",
        description="Asigna un curso a un grado dentro de un ciclo escolar.",
        tags=CATALOGUE,
        request=CurriculumPlanCreateSerializer,
        responses={201: CurriculumPlanSerializer},
    ),
)
class CurriculumPlanListCreateView(CatalogueListCreateView):
    list_serializer = CurriculumPlanSerializer
    create_serializer = CurriculumPlanCreateSerializer
    search_fields = CURRICULUM_PLAN_SEARCH
    orderings = CURRICULUM_PLAN_ORDERINGS

    def list_queryset(self, request):
        return queries.curriculum_plans(
            self.institution,
            include_inactive=_include_inactive(request),
            academic_cycle_id=request.query_params.get("academic_cycle_id"),
            grade_id=request.query_params.get("grade_id"),
        )

    def create(self, request, payload):
        academic_cycle = queries.academic_cycle_or_404(
            self.institution, payload["academic_cycle_id"]
        )
        grade = queries.grade_for_payload(self.institution, payload["grade_id"])
        subject = _resolve_subject(payload["subject_id"])
        plan = services.create_curriculum_plan(
            academic_cycle=academic_cycle,
            grade=grade,
            subject=subject,
            is_required=payload.get("is_required", True),
            actor=request.user,
        )
        return queries.curriculum_plan_or_404(self.institution, plan.public_id)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar entrada del plan de estudios",
        tags=CATALOGUE,
        responses={200: CurriculumPlanSerializer},
    ),
    patch=extend_schema(
        summary="Actualizar entrada del plan de estudios",
        tags=CATALOGUE,
        request=CurriculumPlanUpdateSerializer,
        responses={200: CurriculumPlanSerializer},
    ),
    delete=extend_schema(
        summary="Quitar curso del plan de estudios",
        description=(
            "Desactiva la entrada en lugar de eliminarla. Se rechaza si el ciclo ya no "
            "esta en planificacion."
        ),
        tags=CATALOGUE,
        responses={204: None},
    ),
)
class CurriculumPlanDetailView(RetrieveMixin, UpdateMixin, DeactivateMixin, CatalogueDetailView):
    detail_serializer = CurriculumPlanSerializer
    update_serializer = CurriculumPlanUpdateSerializer

    def get_object(self, public_id):
        return queries.curriculum_plan_or_404(self.institution, public_id)

    def update(self, request, plan, payload):
        services.update_curriculum_plan(plan=plan, actor=request.user, **payload)

    def deactivate(self, request, plan):
        services.deactivate_curriculum_plan(plan=plan, actor=request.user)


# --------------------------------------------------------------------------- #
# teaching assignments
# --------------------------------------------------------------------------- #


def _optional_bool(value):
    """`true`/`false` (y 1/0, yes/no) del query string; cualquier otra cosa es "sin filtro"."""
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    return None


@extend_schema_view(
    get=extend_schema(
        summary="Listar asignaciones docentes",
        description=(
            "AD2/AD4: filtra en el servidor por ciclo, sección, curso, docente y vigencia "
            "(`current=true` solo vigentes, `current=false` solo finalizadas). Cada fila "
            "trae los nombres de sección, curso y docente."
        ),
        tags=CATALOGUE,
        parameters=[
            OpenApiParameter("academic_cycle_id", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("section_id", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("subject_id", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("teacher_id", str, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("current", bool, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: TeachingAssignmentSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Crear asignacion docente",
        description=(
            "Registra la asignacion vigente de un curso y seccion. PostgreSQL impide periodos "
            "solapados para el mismo ciclo, seccion y curso."
        ),
        tags=CATALOGUE,
        request=TeachingAssignmentCreateSerializer,
        responses={201: TeachingAssignmentSerializer},
    ),
)
class TeachingAssignmentListCreateView(CatalogueView):
    def get(self, request):
        self.require_assignment_scope()
        params = request.query_params
        academic_cycle_id = params.get("academic_cycle_id")
        section_id = params.get("section_id")
        subject_id = params.get("subject_id")
        teacher_id = params.get("teacher_id")
        page = self.paginate_queryset(
            queries.teaching_assignments(
                self.institution,
                academic_cycle=(
                    queries.academic_cycle_for_payload(academic_cycle_id)
                    if academic_cycle_id
                    else None
                ),
                section=queries.section_for_payload(section_id) if section_id else None,
                subject=queries.subject_for_payload(subject_id) if subject_id else None,
                teacher=(
                    teacher_queries.teacher_for_payload(teacher_id).person if teacher_id else None
                ),
                current=_optional_bool(params.get("current")),
            )
        )
        return self.get_paginated_response(TeachingAssignmentSerializer(page, many=True).data)

    def post(self, request):
        self.require_assignment_scope()
        payload = self.validated(TeachingAssignmentCreateSerializer, request)
        academic_cycle = queries.academic_cycle_for_payload(payload["academic_cycle_id"])
        if academic_cycle.institution_id != self.institution.id:
            raise DomainError("El ciclo escolar debe pertenecer a la institucion actual.")
        assignment = services.create_teaching_assignment(
            academic_cycle=academic_cycle,
            section=queries.section_for_payload(payload["section_id"]),
            subject=queries.subject_for_payload(payload["subject_id"]),
            teacher=teacher_queries.teacher_for_payload(payload["teacher_id"]).person,
            starts_on=payload.get("starts_on"),
            actor=request.user,
        )
        return Response(
            TeachingAssignmentSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema_view(
    post=extend_schema(
        summary="Reasignar docente",
        description=(
            "Cierra la asignacion vigente en `ends_on` y crea otra para el nuevo docente al dia "
            "siguiente, sin modificar el historial."
        ),
        tags=CATALOGUE,
        request=TeachingAssignmentReassignSerializer,
        responses={201: TeachingAssignmentSerializer},
    ),
)
class TeachingAssignmentReassignView(CatalogueView):
    def post(self, request, public_id):
        self.require_assignment_scope()
        payload = self.validated(TeachingAssignmentReassignSerializer, request)
        assignment = queries.teaching_assignment_or_404(public_id)
        if assignment.academic_cycle.institution_id != self.institution.id:
            raise DomainError("La asignacion docente debe pertenecer a la institucion actual.")
        successor = services.reassign_teaching_assignment(
            assignment=assignment,
            teacher=teacher_queries.teacher_for_payload(payload["teacher_id"]).person,
            ends_on=payload["ends_on"],
            actor=request.user,
        )
        return Response(
            TeachingAssignmentSerializer(successor).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    summary="Consultar historial de asignaciones docentes",
    description="Filtra opcionalmente por perfil Teacher y ciclo escolar mediante sus public IDs.",
    tags=CATALOGUE,
    parameters=[
        OpenApiParameter("teacher_id", str, OpenApiParameter.QUERY, required=False),
        OpenApiParameter("academic_cycle_id", str, OpenApiParameter.QUERY, required=False),
    ],
    responses={200: TeachingAssignmentSerializer(many=True)},
)
class TeachingAssignmentHistoryView(CatalogueView):
    def get(self, request):
        self.require_assignment_scope()
        teacher_id = request.query_params.get("teacher_id")
        academic_cycle_id = request.query_params.get("academic_cycle_id")
        teacher = teacher_queries.teacher_for_payload(teacher_id).person if teacher_id else None
        academic_cycle = (
            queries.academic_cycle_for_payload(academic_cycle_id) if academic_cycle_id else None
        )
        page = self.paginate_queryset(
            queries.teaching_assignment_history(
                self.institution, teacher=teacher, academic_cycle=academic_cycle
            )
        )
        return self.get_paginated_response(TeachingAssignmentSerializer(page, many=True).data)


class CycleAssignmentMatrixView(CatalogueView):
    @extend_schema(
        summary="Matriz sección × curso del ciclo",
        description=(
            "AD3: una fila por sección activa del ciclo (paginada por sección) con una celda "
            "por curso del plan de estudios de su grado y la asignación vigente de esa celda, "
            "o `null` si falta docente. `grade_id` limita a un grado."
        ),
        tags=CATALOGUE,
        parameters=[OpenApiParameter("grade_id", str, OpenApiParameter.QUERY, required=False)],
        responses={200: AssignmentMatrixRowSerializer(many=True)},
    )
    def get(self, request, public_id):
        self.require_assignment_scope()
        cycle = queries.academic_cycle_or_404(self.institution, public_id)
        grade_id = request.query_params.get("grade_id")
        grade = queries.grade_for_payload(self.institution, grade_id) if grade_id else None
        page = self.paginate_queryset(queries.assignment_matrix_sections(cycle, grade=grade))
        rows = queries.assignment_matrix_rows(cycle, page)
        return self.get_paginated_response(AssignmentMatrixRowSerializer(rows, many=True).data)


class CycleTeachingAssignmentClonePreviewView(CatalogueView):
    @extend_schema(
        summary="Previsualizar el clonado de asignaciones hacia este ciclo",
        description=(
            "AD2: compara las asignaciones vigentes del ciclo `source_cycle_id` con este "
            "ciclo y devuelve, por fila, la sección equivalente (mismo grado, jornada y "
            "nombre) y si queda `pending`, `already_assigned` o `unmatched`. No escribe nada; "
            "se aplica con `POST …/teaching-assignments/batch/`."
        ),
        tags=CATALOGUE,
        parameters=[
            OpenApiParameter("source_cycle_id", str, OpenApiParameter.QUERY, required=True)
        ],
        responses={200: CloneAssignmentPreviewSerializer},
    )
    def get(self, request, public_id):
        self.require_assignment_scope()
        target = queries.academic_cycle_or_404(self.institution, public_id)
        source_id = request.query_params.get("source_cycle_id")
        if not source_id:
            raise DomainError("Indique el ciclo de origen (source_cycle_id).")
        source = queries.academic_cycle_for_payload(source_id)
        if source.institution_id != self.institution.id:
            raise DomainError("El ciclo de origen debe pertenecer a la institución actual.")
        if source.pk == target.pk:
            raise DomainError("Elija un ciclo de origen distinto al ciclo destino.")
        preview = queries.teaching_assignment_clone_preview(
            source_cycle=source, target_cycle=target
        )
        return Response(CloneAssignmentPreviewSerializer(preview).data)


class CycleTeachingAssignmentBatchView(CatalogueView):
    @extend_schema(
        summary="Crear varias asignaciones docentes del ciclo",
        description=(
            "AD2: alta por lotes para «Asignar por lotes» y «Clonar asignaciones». Cada "
            "elemento se valida y se guarda por separado: uno rechazado no cancela los demás. "
            "Responde 201 con las creadas y los rechazos con su motivo."
        ),
        tags=CATALOGUE,
        request=TeachingAssignmentBatchSerializer,
        responses={201: TeachingAssignmentBatchResultSerializer},
    )
    def post(self, request, public_id):
        self.require_assignment_scope()
        payload = self.validated(TeachingAssignmentBatchSerializer, request)
        cycle = queries.academic_cycle_or_404(self.institution, public_id)
        created, failed = services.create_teaching_assignments_batch(
            academic_cycle=cycle,
            items=payload["items"],
            starts_on=payload.get("starts_on"),
            actor=request.user,
        )
        return Response(
            TeachingAssignmentBatchResultSerializer({"created": created, "failed": failed}).data,
            status=status.HTTP_201_CREATED,
        )


# --------------------------------------------------------------------------- #
# form suggestions
#
# The codes and the cycle dates are generated by the domain services. The form
# still SHOWS them before saving, because a field that fills itself the moment
# you submit reads as data loss, and because these values stay editable — a
# transferred student arrives with a code already printed on their papers.
#
# Read-only and derived from the same functions the services use, so the value
# offered here is the value that would be stored.
# --------------------------------------------------------------------------- #


SUGGESTIONS = ["academics: suggestions"]


@extend_schema_view(
    get=extend_schema(
        summary="Sugerir codigo de sede",
        tags=SUGGESTIONS,
        responses={200: SuggestedCodeSerializer},
    )
)
class CampusNextCodeView(CatalogueView):
    serializer_class = SuggestedCodeSerializer

    def get(self, request):
        code = services.next_campus_code(institution=self.institution)
        return Response(SuggestedCodeSerializer({"code": code}).data)


@extend_schema_view(
    get=extend_schema(
        summary="Sugerir codigo de nivel",
        tags=SUGGESTIONS,
        responses={200: SuggestedCodeSerializer},
    )
)
class LevelNextCodeView(CatalogueView):
    serializer_class = SuggestedCodeSerializer

    def get(self, request):
        code = services.next_level_code(institution=self.institution)
        return Response(SuggestedCodeSerializer({"code": code}).data)


@extend_schema_view(
    get=extend_schema(
        summary="Sugerir codigo de grado",
        description="Derivado del codigo del nivel: BAS1, BAS2.",
        tags=SUGGESTIONS,
        responses={200: SuggestedCodeSerializer},
    )
)
class LevelGradeNextCodeView(CatalogueView):
    serializer_class = SuggestedCodeSerializer

    def get(self, request, public_id):
        level = queries.level_or_404(self.institution, public_id)
        return Response(
            SuggestedCodeSerializer({"code": services.next_grade_code(level=level)}).data
        )


@extend_schema_view(
    get=extend_schema(
        summary="Sugerir nombre y vigencia de un ciclo",
        description=(
            "Nombre y fechas que tomaria el ciclo del anio consultado, sin crearlo. "
            "Sin `year`, propone el siguiente al ciclo mas reciente de la institucion."
        ),
        tags=SUGGESTIONS,
        parameters=[YEAR],
        responses={200: AcademicCycleDefaultsSerializer},
    )
)
class AcademicCycleDefaultsView(CatalogueView):
    serializer_class = AcademicCycleDefaultsSerializer

    def get(self, request):
        return Response(
            AcademicCycleDefaultsSerializer(
                services.academic_cycle_defaults(self._year(request))
            ).data
        )

    def _year(self, request):
        """
        El anio pedido, o el siguiente al ultimo ciclo registrado.

        Sin ciclos todavia se propone el anio corriente: un establecimiento que
        estrena el sistema esta registrando el ciclo en curso, no el que viene.
        """
        requested = request.query_params.get("year")
        if requested:
            try:
                return int(requested)
            except ValueError as exc:
                raise DomainError("El anio debe ser un numero entero.") from exc

        latest = queries.latest_cycle_year(self.institution)
        return latest + 1 if latest else timezone.localdate().year


class FrozenSubjectResultView(GenericAPIView):
    """
    Current frozen result of one subarea for a closed cycle (RF-RES-007).

    Base: /api/v1/academics/cycles/{cycle_public_id}

    GET {base}/enrolments/{enrolment_id}/subjects/{subject_id}/frozen-result/
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FrozenSubjectResultSerializer

    @extend_schema(
        summary="Consultar el resultado congelado de una subarea",
        description=(
            "Valor definitivo fijado al cerrar el ciclo (RF-RES-007). No se recalcula: "
            "cambios posteriores en configuracion de evaluacion o estructura academica "
            "no lo alteran."
        ),
        responses={200: FrozenSubjectResultSerializer},
        tags=["academics: cycles"],
    )
    def get(self, request, cycle_public_id, enrolment_id, subject_id):
        enrolment, subject = _resolve_enrolment_subject(cycle_public_id, enrolment_id, subject_id)
        result = queries.latest_frozen_subject_result(enrolment=enrolment, subject=subject)
        if result is None:
            raise ResourceNotFoundError(
                "El ciclo aun no tiene un resultado congelado para esta subarea."
            )
        return Response(FrozenSubjectResultSerializer(result).data)


class FrozenSubjectResultListView(GenericAPIView):
    """
    Current frozen result of every subarea of an enrolment (V5: the report
    card in one call instead of one call per subarea).

    Base: /api/v1/academics/cycles/{cycle_public_id}

    GET {base}/enrolments/{enrolment_id}/frozen-results/
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FrozenSubjectResultSerializer

    @extend_schema(
        summary="Consultar los resultados congelados de una matrícula",
        description=(
            "El resultado vigente (la corrección más reciente, si la hubo) de cada "
            "subárea, ordenado por nombre de la subárea. Lista sin paginar, acotada "
            "por el plan de estudios; vacía si el ciclo aún no se cerró. Mismo "
            "permiso que la consulta por subárea (sesión; ver #643)."
        ),
        responses={200: FrozenSubjectResultSerializer(many=True)},
        tags=["academics: cycles"],
    )
    def get(self, request, cycle_public_id, enrolment_id):
        enrolment = evaluation_queries.enrolment_or_none(
            cycle_public_id=cycle_public_id, enrolment_id=enrolment_id
        )
        if enrolment is None:
            raise ResourceNotFoundError("No se encontró la matrícula.")
        results = queries.current_frozen_subject_results(enrolment=enrolment)
        return Response(FrozenSubjectResultSerializer(results, many=True).data)


class FrozenSubjectResultCorrectionView(GenericAPIView):
    """
    Correct a subarea's frozen result via the exceptional academic-authorization
    gap (RF-RES-007, Escenario 2).

    Base: /api/v1/academics/cycles/{cycle_public_id}

    POST {base}/enrolments/{enrolment_id}/subjects/{subject_id}/frozen-result/correct/
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FrozenSubjectResultCorrectionSerializer

    @extend_schema(
        summary="Corregir el resultado congelado de una subarea",
        description=(
            "Exige el permiso atomico grade.correct y un motivo obligatorio. No "
            "reemplaza el resultado congelado anterior: lo conserva y agrega uno "
            "nuevo con la traza del cambio."
        ),
        request=FrozenSubjectResultCorrectionSerializer,
        responses={201: FrozenSubjectResultSerializer},
        tags=["academics: cycles"],
    )
    def post(self, request, cycle_public_id, enrolment_id, subject_id):
        if not request.user.has_atomic_permission("grade_correct"):
            raise AuthorizationError("El actor no tiene el permiso requerido.")

        enrolment, subject = _resolve_enrolment_subject(cycle_public_id, enrolment_id, subject_id)
        current = queries.latest_frozen_subject_result(enrolment=enrolment, subject=subject)
        if current is None:
            raise ResourceNotFoundError(
                "El ciclo aun no tiene un resultado congelado para esta subarea."
            )

        payload = self.validated(FrozenSubjectResultCorrectionSerializer, request)
        corrected = services.correct_frozen_subject_result(
            frozen_result=current,
            final_grade=payload["final_grade"],
            reason=payload["reason"],
            actor=request.user,
        )
        return Response(
            FrozenSubjectResultSerializer(corrected).data, status=status.HTTP_201_CREATED
        )

    def validated(self, serializer_class, request):
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class FrozenPromotionResultView(GenericAPIView):
    """
    Current frozen promotion outcome of an enrolment for a closed cycle (RF-RES-007).

    Base: /api/v1/academics/cycles/{cycle_public_id}

    GET {base}/enrolments/{enrolment_id}/frozen-promotion/
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FrozenPromotionResultSerializer

    @extend_schema(
        summary="Consultar la condicion de promocion congelada",
        responses={200: FrozenPromotionResultSerializer},
        tags=["academics: cycles"],
    )
    def get(self, request, cycle_public_id, enrolment_id):
        enrolment = evaluation_queries.enrolment_or_none(
            cycle_public_id=cycle_public_id, enrolment_id=enrolment_id
        )
        if enrolment is None:
            raise ResourceNotFoundError("No se encontró la matrícula.")
        result = queries.latest_frozen_promotion_result(enrolment=enrolment)
        if result is None:
            raise ResourceNotFoundError(
                "El ciclo aun no tiene una condicion de promocion congelada."
            )
        return Response(FrozenPromotionResultSerializer(result).data)


def _resolve_enrolment_subject(cycle_public_id, enrolment_id, subject_id):
    """Same resolution evaluation's equivalent endpoints use (RF-RES-001/004/005):
    the enrolment must belong to the cycle in the URL, the subject just needs
    to exist and be active."""
    enrolment = evaluation_queries.enrolment_or_none(
        cycle_public_id=cycle_public_id, enrolment_id=enrolment_id
    )
    if enrolment is None:
        raise ResourceNotFoundError("No se encontró la matrícula.")

    subject = evaluation_queries.subject_or_none(subject_id)
    if subject is None:
        raise ResourceNotFoundError("No se encontró el curso.")

    return enrolment, subject


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _resolve_subject(public_id):
    """
    Resolved without an institution filter on purpose: the service must be the
    one reporting a cross-institution pairing, instead of the API hiding it
    behind a generic "not found".
    """
    return queries.subject_for_payload(public_id)
