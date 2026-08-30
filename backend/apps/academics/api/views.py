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

from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.academics import queries, services
from apps.common.exceptions import AuthorizationError, DomainError
from apps.teachers import queries as teacher_queries

from .serializers import (
    AcademicCycleCloneSerializer,
    AcademicCycleCreateSerializer,
    AcademicCycleDefaultsSerializer,
    AcademicCycleSerializer,
    CampusCreateSerializer,
    CampusSerializer,
    CampusUpdateSerializer,
    ClassroomCreateSerializer,
    ClassroomSerializer,
    ClassroomUpdateSerializer,
    ClassScheduleBlockCreateSerializer,
    ClassScheduleBlockSerializer,
    ClassScheduleBlockUpdateSerializer,
    ClassSchedulePublicationSerializer,
    ClassSessionCreateSerializer,
    ClassSessionSerializer,
    CurriculumPlanCreateSerializer,
    CurriculumPlanSerializer,
    CurriculumPlanUpdateSerializer,
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
    TeachingAssignmentCreateSerializer,
    TeachingAssignmentReassignSerializer,
    TeachingAssignmentSerializer,
)

CATALOGUE = ["academics: catalogue"]

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
            raise AuthorizationError("Actor lacks the required permission or institution scope.")


class CatalogueListCreateView(CatalogueView):
    """
    ``GET`` lists a queryset, paginated; ``POST`` delegates to a service.

    Subclasses provide ``list_serializer``, ``create_serializer``,
    ``list_queryset(request, **kwargs)`` and ``create(request, payload, **kwargs)``.
    """

    list_serializer = None
    create_serializer = None

    def get_serializer_class(self):
        if self.request.method == "POST":
            return self.create_serializer
        return self.list_serializer

    def get(self, request, **kwargs):
        page = self.paginate_queryset(self.list_queryset(request, **kwargs))
        return self.get_paginated_response(self.list_serializer(page, many=True).data)

    def post(self, request, **kwargs):
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
        payload = self.validated(self.update_serializer, request)
        self.update(request, self.get_object(**kwargs), payload)
        return self.represent(self.get_object(**kwargs))


class DeactivateMixin:
    def delete(self, request, **kwargs):
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
class AcademicCycleListCreateView(CatalogueListCreateView):
    list_serializer = AcademicCycleSerializer
    create_serializer = AcademicCycleCreateSerializer

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


class AcademicCycleActivateView(CatalogueView):
    @extend_schema(
        summary="Activar ciclo escolar",
        tags=["academics: cycles"],
        request=None,
        responses={200: AcademicCycleSerializer},
    )
    def post(self, request, public_id):
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
        cycle = queries.academic_cycle_or_404(self.institution, public_id)
        closed = services.close_academic_cycle(cycle=cycle, actor=request.user)
        return Response(AcademicCycleSerializer(closed).data)


class AcademicCycleCloneView(CatalogueView):
    serializer_class = AcademicCycleCloneSerializer

    @extend_schema(
        summary="Clonar estructura hacia un ciclo nuevo",
        tags=["academics: cycles"],
        request=AcademicCycleCloneSerializer,
        responses={201: AcademicCycleSerializer},
    )
    def post(self, request, public_id):
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
        parameters=[INCLUDE_INACTIVE],
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
class CampusListCreateView(CatalogueListCreateView):
    list_serializer = CampusSerializer
    create_serializer = CampusCreateSerializer

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
# shifts ("jornadas") — always under a campus
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar jornadas de una sede",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE],
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
class CampusShiftListCreateView(CatalogueListCreateView):
    list_serializer = ShiftSerializer
    create_serializer = ShiftCreateSerializer

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
# classrooms ("aulas") -- RF-AUL-001
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar aulas",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE],
        responses={200: ClassroomSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Registrar aula",
        tags=CATALOGUE,
        request=ClassroomCreateSerializer,
        responses={201: ClassroomSerializer},
    ),
)
class CampusClassroomListCreateView(CatalogueListCreateView):
    list_serializer = ClassroomSerializer
    create_serializer = ClassroomCreateSerializer

    def list_queryset(self, request, public_id):
        return queries.classrooms(
            queries.campus_or_404(self.institution, public_id),
            include_inactive=_include_inactive(request),
        )

    def create(self, request, payload, public_id):
        campus = queries.campus_or_404(self.institution, public_id)
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
    delete=extend_schema(
        summary="Desactivar aula",
        tags=CATALOGUE,
        responses={204: None},
    ),
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
        parameters=[INCLUDE_INACTIVE],
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
class LevelListCreateView(CatalogueListCreateView):
    list_serializer = LevelSerializer
    create_serializer = LevelCreateSerializer

    def list_queryset(self, request):
        return queries.levels(self.institution, include_inactive=_include_inactive(request))

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
        parameters=[INCLUDE_INACTIVE],
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
        parameters=[INCLUDE_INACTIVE],
        responses={200: SubjectSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Crear curso",
        tags=CATALOGUE,
        request=SubjectCreateSerializer,
        responses={201: SubjectSerializer},
    ),
)
class SubjectListCreateView(CatalogueListCreateView):
    list_serializer = SubjectSerializer
    create_serializer = SubjectCreateSerializer

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
class SectionListCreateView(CatalogueListCreateView):
    list_serializer = SectionSerializer
    create_serializer = SectionCreateSerializer

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
        section = services.create_section(
            academic_cycle=academic_cycle,
            grade=grade,
            shift=shift,
            name=payload["name"],
            capacity=payload.get("capacity", 0),
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
        services.update_section(section=section, actor=request.user, **payload)

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
        return services.create_class_session(
            academic_cycle=section.academic_cycle,
            section=section,
            subject=subject,
            schedule_block=schedule_block,
            day_of_week=payload["day_of_week"],
            actor=request.user,
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
        cycle = queries.academic_cycle_or_404(self.institution, public_id)
        publication = services.publish_class_schedule(academic_cycle=cycle, actor=request.user)
        return Response(ClassSchedulePublicationSerializer(publication).data)

    def delete(self, request, public_id):
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


@extend_schema_view(
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
