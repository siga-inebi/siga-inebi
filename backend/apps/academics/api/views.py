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
from apps.academics.models import AcademicCycle, Grade, Shift, Subject
from apps.common.models import DomainError
from apps.common.parsing import parse_uuid

from .serializers import (
    AcademicCycleCreateSerializer,
    AcademicCycleDetailSerializer,
    AcademicCycleListSerializer,
    CampusCreateSerializer,
    CampusSerializer,
    CampusUpdateSerializer,
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
)

CATALOGUE = ["academics: catalogue"]
CYCLES = ["academics: cycles"]

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


# --------------------------------------------------------------------------- #
# cycles
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar ciclos escolares",
        tags=CYCLES,
        responses={200: AcademicCycleListSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Crear ciclo en borrador",
        tags=CYCLES,
        request=AcademicCycleCreateSerializer,
        responses={201: AcademicCycleListSerializer},
    ),
)
class AcademicCycleListCreateView(CatalogueListCreateView):
    list_serializer = AcademicCycleListSerializer
    create_serializer = AcademicCycleCreateSerializer

    def list_queryset(self, request):
        return queries.cycles_all(self.institution)

    def create(self, request, payload):
        return AcademicCycle.objects.create(
            institution=self.institution,
            status=AcademicCycle.CycleStatus.DRAFT,
            **payload,
        )


@extend_schema_view(
    get=extend_schema(
        summary="Consultar ciclo",
        description=(
            "Resumen del ciclo con el numero de ofertas y secciones. Las secciones se "
            "consultan paginadas en `offerings/{id}/sections/`."
        ),
        tags=CYCLES,
        responses={200: AcademicCycleDetailSerializer},
    ),
)
class AcademicCycleDetailView(RetrieveMixin, CatalogueDetailView):
    detail_serializer = AcademicCycleDetailSerializer

    def get_object(self, public_id):
        return queries.cycle_or_404(self.institution, public_id)


class AcademicCycleTransitionView(CatalogueView):
    """Shared body for the open/close transitions."""

    serializer_class = AcademicCycleListSerializer
    transition = None

    def post(self, request, public_id):
        cycle = queries.cycle_or_404(self.institution, public_id)
        type(self).transition(cycle=cycle, actor=request.user)
        return Response(AcademicCycleListSerializer(cycle).data)


@extend_schema_view(
    post=extend_schema(
        summary="Abrir ciclo",
        description="Pasa el ciclo de borrador a activo (RF-CIC-003).",
        tags=CYCLES,
        request=None,
        responses={200: AcademicCycleListSerializer},
    ),
)
class AcademicCycleOpenView(AcademicCycleTransitionView):
    transition = staticmethod(services.open_cycle)


@extend_schema_view(
    post=extend_schema(
        summary="Cerrar ciclo",
        description="Pasa el ciclo de activo a cerrado y congela su estructura (RF-CIC-004).",
        tags=CYCLES,
        request=None,
        responses={200: AcademicCycleListSerializer},
    ),
)
class AcademicCycleCloseView(AcademicCycleTransitionView):
    transition = staticmethod(services.close_cycle)


# --------------------------------------------------------------------------- #
# grade offerings — the catalogue enrolments are assigned to
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar la oferta de grados del ciclo",
        description=(
            "Cada elemento es un grado ofertado en una jornada de una sede. "
            "Los filtros aceptan public IDs; un ID inexistente devuelve una lista vacia "
            "y un ID mal formado devuelve 400."
        ),
        tags=CYCLES,
        parameters=[
            OpenApiParameter("campus", str, description="Filtra por sede."),
            OpenApiParameter("shift", str, description="Filtra por jornada."),
            OpenApiParameter("level", str, description="Filtra por nivel."),
            OpenApiParameter("grade", str, description="Filtra por grado."),
        ],
        responses={200: GradeOfferingSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Ofertar un grado en una jornada",
        description=(
            "Agrega un grado a la oferta del ciclo. La jornada determina la sede. "
            "Se rechaza si el ciclo esta cerrado, si hay mezcla de instituciones, "
            "si algun elemento esta inactivo o si la combinacion ya existe."
        ),
        tags=CYCLES,
        request=GradeOfferingCreateSerializer,
        responses={201: GradeOfferingSerializer},
    ),
)
class CycleOfferingListCreateView(CatalogueListCreateView):
    list_serializer = GradeOfferingSerializer
    create_serializer = GradeOfferingCreateSerializer

    FILTERS = (
        ("campus", "shift__campus__public_id"),
        ("shift", "shift__public_id"),
        ("level", "grade__level__public_id"),
        ("grade", "grade__public_id"),
    )

    def list_queryset(self, request, cycle_public_id):
        cycle = queries.cycle_or_404(self.institution, cycle_public_id)
        queryset = queries.offerings(cycle)

        for param, lookup in self.FILTERS:
            value = parse_uuid(request.query_params.get(param), field=param)
            if value is not None:
                queryset = queryset.filter(**{lookup: value})

        return queryset

    def create(self, request, payload, cycle_public_id):
        cycle = queries.cycle_or_404(self.institution, cycle_public_id)
        grade = _resolve(Grade.objects.select_related("level"), payload["grade_id"], "Grade")
        shift = _resolve(Shift.objects.select_related("campus"), payload["shift_id"], "Shift")

        offering = services.create_grade_offering(
            cycle=cycle, shift=shift, grade=grade, actor=request.user
        )
        return queries.offering_or_404(self.institution, offering.public_id)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar una oferta de grado",
        tags=CYCLES,
        responses={200: GradeOfferingSerializer},
    ),
    delete=extend_schema(
        summary="Quitar una oferta de grado",
        description="Se rechaza si el ciclo esta cerrado o si la oferta aun tiene secciones.",
        tags=CYCLES,
        responses={204: None},
    ),
)
class GradeOfferingDetailView(RetrieveMixin, DeactivateMixin, CatalogueDetailView):
    detail_serializer = GradeOfferingSerializer

    def get_object(self, public_id):
        return queries.offering_or_404(self.institution, public_id)

    def deactivate(self, request, offering):
        services.remove_grade_offering(offering=offering, actor=request.user)


# --------------------------------------------------------------------------- #
# sections
# --------------------------------------------------------------------------- #


@extend_schema_view(
    get=extend_schema(
        summary="Listar secciones de una oferta",
        description="Incluye ocupacion activa y cupos libres (RF-EST-008).",
        tags=CYCLES,
        parameters=[INCLUDE_INACTIVE],
        responses={200: SectionSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Crear seccion en una oferta",
        description="El nombre se normaliza a mayusculas y es unico dentro de la oferta.",
        tags=CYCLES,
        request=SectionCreateSerializer,
        responses={201: SectionSerializer},
    ),
)
class OfferingSectionListCreateView(CatalogueListCreateView):
    list_serializer = SectionSerializer
    create_serializer = SectionCreateSerializer

    def list_queryset(self, request, public_id):
        offering = queries.offering_or_404(self.institution, public_id)
        return queries.sections(request, offering=offering)

    def create(self, request, payload, public_id):
        offering = queries.offering_or_404(self.institution, public_id)
        section = services.create_section(offering=offering, actor=request.user, **payload)
        return queries.section_or_404(self.institution, section.public_id)


@extend_schema_view(
    get=extend_schema(summary="Consultar seccion", tags=CYCLES, responses={200: SectionSerializer}),
    patch=extend_schema(
        summary="Actualizar seccion",
        description="La capacidad no puede quedar por debajo de la ocupacion actual.",
        tags=CYCLES,
        request=SectionUpdateSerializer,
        responses={200: SectionSerializer},
    ),
    delete=extend_schema(
        summary="Desactivar seccion",
        description="Se rechaza mientras la seccion tenga matriculas activas.",
        tags=CYCLES,
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
