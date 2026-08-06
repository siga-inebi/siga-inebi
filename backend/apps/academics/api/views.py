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

from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.academics import services
from apps.academics.api import queries
from apps.academics.models import Grade, Shift, Subject
from apps.common.models import DomainError
from apps.people.models import Person

from .serializers import (
    AcademicCycleCreateSerializer,
    AcademicCycleSerializer,
    AcademicCycleStatusSerializer,
    AcademicCycleUpdateSerializer,
    CampusCreateSerializer,
    CampusSerializer,
    CampusUpdateSerializer,
    CurriculumPlanCreateSerializer,
    CurriculumPlanSerializer,
    CurriculumPlanUpdateSerializer,
    GradeCreateSerializer,
    GradeOfferingCreateSerializer,
    GradeOfferingSerializer,
    GradeSerializer,
    GradeUpdateSerializer,
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
    TeachingAssignmentCreateSerializer,
    TeachingAssignmentEndSerializer,
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


# --------------------------------------------------------------------------- #
# base classes
# --------------------------------------------------------------------------- #


class CatalogueView(GenericAPIView):
    """Authenticated access plus the institution the request operates on."""

    permission_classes = [permissions.IsAuthenticated]

    @property
    def institution(self):
        if not hasattr(self, "_institution"):
            self._institution = queries.resolve_institution(self.request)
        return self._institution

    def validated(self, serializer_class, request):
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


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
        return queries.campuses(self.institution, request)

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
        return queries.shifts(queries.campus_or_404(self.institution, public_id), request)

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
        return queries.levels(self.institution, request)

    def create(self, request, payload):
        level = services.create_level(institution=self.institution, actor=request.user, **payload)
        return queries.level_or_404(self.institution, level.public_id)


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
        services.update_level(level=level, actor=request.user, **payload)

    def deactivate(self, request, level):
        services.deactivate_level(level=level, actor=request.user)


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
        return queries.grades(queries.level_or_404(self.institution, public_id), request)

    def create(self, request, payload, public_id):
        level = queries.level_or_404(self.institution, public_id)
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
        return queries.subjects(self.institution, request)

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
# academic cycles ("ciclos escolares")
# --------------------------------------------------------------------------- #

CYCLE = ["academics: cycle"]


@extend_schema_view(
    get=extend_schema(
        summary="Listar ciclos escolares",
        description="Ciclos de la institucion, del mas reciente al mas antiguo.",
        tags=CYCLE,
        parameters=[INCLUDE_INACTIVE],
        responses={200: AcademicCycleSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Crear ciclo escolar",
        description=(
            "Abre un ciclo en estado `draft`. La estructura se arma primero y el "
            "ciclo se activa despues, cuando ya tiene al menos una oferta de grado."
        ),
        tags=CYCLE,
        request=AcademicCycleCreateSerializer,
        responses={201: AcademicCycleSerializer},
    ),
)
class CycleListCreateView(CatalogueListCreateView):
    list_serializer = AcademicCycleSerializer
    create_serializer = AcademicCycleCreateSerializer

    def list_queryset(self, request):
        return queries.cycles(self.institution, request)

    def create(self, request, payload):
        cycle = services.create_academic_cycle(
            institution=self.institution, actor=request.user, **payload
        )
        return queries.cycle_or_404(self.institution, cycle.public_id)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar ciclo escolar", tags=CYCLE, responses={200: AcademicCycleSerializer}
    ),
    patch=extend_schema(
        summary="Actualizar ciclo escolar",
        description="Solo mientras el ciclo no este cerrado (RF-EST-011).",
        tags=CYCLE,
        request=AcademicCycleUpdateSerializer,
        responses={200: AcademicCycleSerializer},
    ),
)
class CycleDetailView(RetrieveMixin, UpdateMixin, CatalogueDetailView):
    """No expone borrado: un ciclo se cierra, no se elimina."""

    detail_serializer = AcademicCycleSerializer
    update_serializer = AcademicCycleUpdateSerializer

    def get_object(self, public_id):
        return queries.cycle_or_404(self.institution, public_id)

    def update(self, request, cycle, payload):
        services.update_academic_cycle(cycle=cycle, actor=request.user, **payload)


@extend_schema(
    summary="Cambiar el estado del ciclo",
    description=(
        "Avanza el ciclo por `draft` -> `active` -> `closed`. No retrocede: las "
        "matriculas ya apuntan a la estructura del ciclo. Activar exige al menos "
        "una oferta de grado."
    ),
    tags=CYCLE,
    request=AcademicCycleStatusSerializer,
    responses={200: AcademicCycleSerializer},
)
class CycleStatusView(CatalogueView):
    serializer_class = AcademicCycleStatusSerializer

    def post(self, request, public_id):
        payload = self.validated(AcademicCycleStatusSerializer, request)
        cycle = queries.cycle_or_404(self.institution, public_id)
        services.change_cycle_status(cycle=cycle, actor=request.user, **payload)
        return Response(
            AcademicCycleSerializer(queries.cycle_or_404(self.institution, public_id)).data
        )


# --------------------------------------------------------------------------- #
# grade offerings ("oferta de grados") — always under a cycle
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar la oferta de grados de un ciclo",
        description="Que grado se imparte en que jornada durante este ciclo.",
        tags=CYCLE,
        parameters=[INCLUDE_INACTIVE],
        responses={200: GradeOfferingSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Ofertar un grado en una jornada",
        description=(
            "Grado y jornada deben estar activos y ser de la misma institucion "
            "que el ciclo. El trio ciclo/jornada/grado es unico."
        ),
        tags=CYCLE,
        request=GradeOfferingCreateSerializer,
        responses={201: GradeOfferingSerializer},
    ),
)
class CycleOfferingListCreateView(CatalogueListCreateView):
    list_serializer = GradeOfferingSerializer
    create_serializer = GradeOfferingCreateSerializer

    def list_queryset(self, request, public_id):
        return queries.cycle_offerings(queries.cycle_or_404(self.institution, public_id), request)

    def create(self, request, payload, public_id):
        cycle = queries.cycle_or_404(self.institution, public_id)
        offering = services.offer_grade(
            cycle=cycle,
            grade=_resolve_grade(payload["grade_id"]),
            shift=_resolve_shift(payload["shift_id"]),
            actor=request.user,
        )
        return queries.offering_or_404(self.institution, offering.public_id)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar oferta de grado", tags=CYCLE, responses={200: GradeOfferingSerializer}
    ),
    delete=extend_schema(
        summary="Retirar la oferta de grado",
        description=(
            "Desactiva la oferta y sus secciones. Se rechaza si alguna seccion "
            "todavia tiene matriculas activas."
        ),
        tags=CYCLE,
        responses={204: None},
    ),
)
class OfferingDetailView(RetrieveMixin, DeactivateMixin, CatalogueDetailView):
    detail_serializer = GradeOfferingSerializer

    def get_object(self, public_id):
        return queries.offering_or_404(self.institution, public_id)

    def deactivate(self, request, offering):
        services.withdraw_grade_offering(offering=offering, actor=request.user)


# --------------------------------------------------------------------------- #
# sections ("secciones") — always under an offering
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar secciones de una oferta",
        description="Incluye ocupacion y cupo disponible (RF-EST-008).",
        tags=CYCLE,
        parameters=[INCLUDE_INACTIVE],
        responses={200: SectionSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Crear seccion",
        description="El nombre se normaliza a mayusculas y es unico dentro de la oferta.",
        tags=CYCLE,
        request=SectionCreateSerializer,
        responses={201: SectionSerializer},
    ),
)
class OfferingSectionListCreateView(CatalogueListCreateView):
    list_serializer = SectionSerializer
    create_serializer = SectionCreateSerializer

    def list_queryset(self, request, public_id):
        return queries.offering_sections(
            queries.offering_or_404(self.institution, public_id), request
        )

    def create(self, request, payload, public_id):
        offering = queries.offering_or_404(self.institution, public_id)
        section = services.create_section(offering=offering, actor=request.user, **payload)
        return queries.section_or_404(self.institution, section.public_id)


@extend_schema_view(
    get=extend_schema(summary="Consultar seccion", tags=CYCLE, responses={200: SectionSerializer}),
    patch=extend_schema(
        summary="Actualizar seccion",
        description="El cupo no puede bajar por debajo de la ocupacion actual.",
        tags=CYCLE,
        request=SectionUpdateSerializer,
        responses={200: SectionSerializer},
    ),
    delete=extend_schema(
        summary="Desactivar seccion",
        description="Se rechaza mientras tenga matriculas activas.",
        tags=CYCLE,
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
# curriculum plan ("plan de estudios del ciclo")
# --------------------------------------------------------------------------- #

GRADE_FILTER = OpenApiParameter(
    name="grade",
    type=str,
    location=OpenApiParameter.QUERY,
    required=False,
    description="Public ID de un grado, para ver solo su plan.",
)


@extend_schema_view(
    get=extend_schema(
        summary="Listar el plan de estudios de un ciclo",
        description=(
            "Que cursos estudia cada grado en este ciclo (RF-EST-005). Es el plan "
            "del ciclo, distinto del catalogo permanente del nivel."
        ),
        tags=CYCLE,
        parameters=[GRADE_FILTER],
        responses={200: CurriculumPlanSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Agregar un curso al plan de un grado",
        description="Grado y curso deben estar activos y ser de la institucion del ciclo.",
        tags=CYCLE,
        request=CurriculumPlanCreateSerializer,
        responses={201: CurriculumPlanSerializer},
    ),
)
class CycleCurriculumListCreateView(CatalogueListCreateView):
    list_serializer = CurriculumPlanSerializer
    create_serializer = CurriculumPlanCreateSerializer

    def list_queryset(self, request, public_id):
        cycle = queries.cycle_or_404(self.institution, public_id)
        grade_public_id = request.query_params.get("grade")
        grade = queries.grade_or_404(self.institution, grade_public_id) if grade_public_id else None
        return queries.curriculum_entries(cycle, grade)

    def create(self, request, payload, public_id):
        cycle = queries.cycle_or_404(self.institution, public_id)
        return services.add_curriculum_entry(
            cycle=cycle,
            grade=_resolve_grade(payload["grade_id"]),
            subject=_resolve_subject(payload["subject_id"]),
            is_required=payload["is_required"],
            actor=request.user,
        )


@extend_schema_view(
    get=extend_schema(
        summary="Consultar entrada del plan",
        tags=CYCLE,
        responses={200: CurriculumPlanSerializer},
    ),
    patch=extend_schema(
        summary="Cambiar la obligatoriedad de un curso del plan",
        tags=CYCLE,
        request=CurriculumPlanUpdateSerializer,
        responses={200: CurriculumPlanSerializer},
    ),
    delete=extend_schema(
        summary="Quitar un curso del plan",
        description=("Se rechaza mientras un docente siga asignado a ese curso en el grado."),
        tags=CYCLE,
        responses={204: None},
    ),
)
class CurriculumEntryDetailView(RetrieveMixin, UpdateMixin, DeactivateMixin, CatalogueDetailView):
    detail_serializer = CurriculumPlanSerializer
    update_serializer = CurriculumPlanUpdateSerializer

    def get_object(self, public_id):
        return queries.curriculum_entry_or_404(self.institution, public_id)

    def update(self, request, entry, payload):
        services.update_curriculum_entry(entry=entry, actor=request.user, **payload)

    def deactivate(self, request, entry):
        services.remove_curriculum_entry(entry=entry, actor=request.user)


# --------------------------------------------------------------------------- #
# teaching assignments ("asignacion de docentes") — always under a section
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar asignaciones docentes de una seccion",
        description=(
            "Solo las vigentes. `include_inactive=true` agrega las ya cerradas, "
            "que se conservan como historia."
        ),
        tags=CYCLE,
        parameters=[INCLUDE_INACTIVE],
        responses={200: TeachingAssignmentSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Asignar un docente a un curso de la seccion",
        description=(
            "El curso debe estar en el plan de estudios del grado para ese ciclo "
            "(RF-EST-009). Solo puede haber una asignacion vigente por curso."
        ),
        tags=CYCLE,
        request=TeachingAssignmentCreateSerializer,
        responses={201: TeachingAssignmentSerializer},
    ),
)
class SectionAssignmentListCreateView(CatalogueListCreateView):
    list_serializer = TeachingAssignmentSerializer
    create_serializer = TeachingAssignmentCreateSerializer

    def list_queryset(self, request, public_id):
        return queries.section_assignments(
            queries.section_or_404(self.institution, public_id), request
        )

    def create(self, request, payload, public_id):
        section = queries.section_or_404(self.institution, public_id)
        return services.assign_teacher(
            section=section,
            subject=_resolve_subject(payload["subject_id"]),
            teacher=_resolve_teacher(payload["teacher_id"]),
            starts_on=payload.get("starts_on"),
            actor=request.user,
        )


@extend_schema_view(
    get=extend_schema(
        summary="Consultar asignacion docente",
        tags=CYCLE,
        responses={200: TeachingAssignmentSerializer},
    ),
    patch=extend_schema(
        summary="Cerrar la asignacion en una fecha",
        description="Libera el curso de la seccion para otro docente.",
        tags=CYCLE,
        request=TeachingAssignmentEndSerializer,
        responses={200: TeachingAssignmentSerializer},
    ),
    delete=extend_schema(
        summary="Cerrar la asignacion hoy",
        description="La fila se conserva como historia; no se borra (ADR-0006).",
        tags=CYCLE,
        responses={204: None},
    ),
)
class AssignmentDetailView(RetrieveMixin, UpdateMixin, DeactivateMixin, CatalogueDetailView):
    """Cerrar es la unica escritura: quien enseno que y hasta cuando es historia."""

    detail_serializer = TeachingAssignmentSerializer
    update_serializer = TeachingAssignmentEndSerializer

    def get_object(self, public_id):
        return queries.assignment_or_404(self.institution, public_id)

    def update(self, request, assignment, payload):
        services.end_teaching_assignment(
            assignment=assignment, ends_on=payload.get("ends_on"), actor=request.user
        )

    def deactivate(self, request, assignment):
        services.end_teaching_assignment(assignment=assignment, actor=request.user)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _resolve(queryset, public_id, label):
    """
    Resolve a reference that arrived in the request body. A bad reference in a
    payload is a bad request, not a missing endpoint, so it lands as a 400.
    """
    try:
        return queryset.get(public_id=public_id)
    except queryset.model.DoesNotExist as exc:
        raise DomainError(f"{label} not found.") from exc


def _resolve_subject(public_id):
    """
    Resolved without an institution filter on purpose: the service must be the
    one reporting a cross-institution pairing, instead of the API hiding it
    behind a generic "not found".
    """
    return _resolve(Subject.objects.all(), public_id, "Subject")


def _resolve_grade(public_id):
    return _resolve(Grade.objects.select_related("level"), public_id, "Grade")


def _resolve_shift(public_id):
    return _resolve(Shift.objects.select_related("campus"), public_id, "Shift")


def _resolve_teacher(public_id):
    return _resolve(Person.objects.all(), public_id, "Teacher")
