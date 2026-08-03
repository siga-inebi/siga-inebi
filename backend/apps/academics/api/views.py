"""
HTTP layer for the academic catalogue.

Views only translate between HTTP and the domain services in
``apps.academics.services``; every invariant lives there. ``DomainError`` is
turned into a 400 envelope by ``config.api.exception_handler``, so no view
catches it (AGENTS.md #8).
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.academics import services
from apps.academics.api import queries
from apps.academics.models import AcademicCycle, Grade, Shift, Subject
from apps.common.models import DomainError

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


class CatalogueView(GenericAPIView):
    """Shared base: authenticated access and the institution of the request."""

    permission_classes = [permissions.IsAuthenticated]

    @property
    def institution(self):
        return queries.resolve_institution(self.request)

    def validated(self, serializer_class, request):
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


# --------------------------------------------------------------------------- #
# campuses ("sedes")
# --------------------------------------------------------------------------- #


class CampusListCreateView(CatalogueView):
    def get_serializer_class(self):
        return CampusCreateSerializer if self.request.method == "POST" else CampusSerializer

    @extend_schema(
        summary="Listar sedes",
        description="Sedes de la institucion. Solo activas salvo `include_inactive=true`.",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE],
        responses={200: CampusSerializer(many=True)},
    )
    def get(self, request):
        queryset = queries.campuses(self.institution, request)
        return Response(CampusSerializer(queryset, many=True).data)

    @extend_schema(
        summary="Crear sede",
        description=(
            "Registra una sede. El codigo se normaliza a mayusculas y es unico por "
            "institucion. Marcar `is_main` degrada la sede principal anterior."
        ),
        tags=CATALOGUE,
        request=CampusCreateSerializer,
        responses={201: CampusSerializer},
    )
    def post(self, request):
        institution = self.institution
        payload = self.validated(CampusCreateSerializer, request)
        campus = services.create_campus(institution=institution, actor=request.user, **payload)
        return Response(
            CampusSerializer(queries.campus_or_404(institution, campus.public_id)).data,
            status=status.HTTP_201_CREATED,
        )


class CampusDetailView(CatalogueView):
    serializer_class = CampusSerializer

    @extend_schema(summary="Consultar sede", tags=CATALOGUE, responses={200: CampusSerializer})
    def get(self, request, public_id):
        campus = queries.campus_or_404(self.institution, public_id)
        return Response(CampusSerializer(campus).data)

    @extend_schema(
        summary="Actualizar sede",
        description="El codigo es inmutable; se actualizan nombre, direccion y sede principal.",
        tags=CATALOGUE,
        request=CampusUpdateSerializer,
        responses={200: CampusSerializer},
    )
    def patch(self, request, public_id):
        institution = self.institution
        campus = queries.campus_or_404(institution, public_id)
        payload = self.validated(CampusUpdateSerializer, request)
        services.update_campus(campus=campus, actor=request.user, **payload)
        return Response(CampusSerializer(queries.campus_or_404(institution, public_id)).data)

    @extend_schema(
        summary="Desactivar sede",
        description=(
            "Desactiva la sede y sus jornadas en lugar de borrarlas (RF-EST-012). "
            "Se rechaza si un ciclo no cerrado usa alguna de sus jornadas."
        ),
        tags=CATALOGUE,
        responses={204: None},
    )
    def delete(self, request, public_id):
        campus = queries.campus_or_404(self.institution, public_id)
        services.deactivate_campus(campus=campus, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------- #
# shifts ("jornadas") — always under a campus
# --------------------------------------------------------------------------- #


class CampusShiftListCreateView(CatalogueView):
    def get_serializer_class(self):
        return ShiftCreateSerializer if self.request.method == "POST" else ShiftSerializer

    @extend_schema(
        summary="Listar jornadas de una sede",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE],
        responses={200: ShiftSerializer(many=True)},
    )
    def get(self, request, public_id):
        campus = queries.campus_or_404(self.institution, public_id)
        return Response(ShiftSerializer(queries.shifts(campus, request), many=True).data)

    @extend_schema(
        summary="Crear jornada en una sede",
        description=(
            "El codigo es unico dentro de la sede, de modo que dos sedes pueden tener MAT."
        ),
        tags=CATALOGUE,
        request=ShiftCreateSerializer,
        responses={201: ShiftSerializer},
    )
    def post(self, request, public_id):
        campus = queries.campus_or_404(self.institution, public_id)
        payload = self.validated(ShiftCreateSerializer, request)
        shift = services.create_shift(campus=campus, actor=request.user, **payload)
        return Response(ShiftSerializer(shift).data, status=status.HTTP_201_CREATED)


class ShiftDetailView(CatalogueView):
    serializer_class = ShiftSerializer

    @extend_schema(summary="Consultar jornada", tags=CATALOGUE, responses={200: ShiftSerializer})
    def get(self, request, public_id):
        return Response(ShiftSerializer(queries.shift_or_404(self.institution, public_id)).data)

    @extend_schema(
        summary="Renombrar jornada",
        tags=CATALOGUE,
        request=ShiftUpdateSerializer,
        responses={200: ShiftSerializer},
    )
    def patch(self, request, public_id):
        shift = queries.shift_or_404(self.institution, public_id)
        payload = self.validated(ShiftUpdateSerializer, request)
        services.update_shift(shift=shift, actor=request.user, **payload)
        return Response(ShiftSerializer(shift).data)

    @extend_schema(
        summary="Desactivar jornada",
        description="Se rechaza si un ciclo no cerrado oferta grados en esta jornada.",
        tags=CATALOGUE,
        responses={204: None},
    )
    def delete(self, request, public_id):
        shift = queries.shift_or_404(self.institution, public_id)
        services.deactivate_shift(shift=shift, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------- #
# levels ("niveles")
# --------------------------------------------------------------------------- #


class LevelListCreateView(CatalogueView):
    def get_serializer_class(self):
        return LevelCreateSerializer if self.request.method == "POST" else LevelSerializer

    @extend_schema(
        summary="Listar niveles",
        description="Niveles ordenados por su secuencia pedagogica.",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE],
        responses={200: LevelSerializer(many=True)},
    )
    def get(self, request):
        return Response(LevelSerializer(queries.levels(self.institution, request), many=True).data)

    @extend_schema(
        summary="Crear nivel",
        description=(
            "Registra un nivel educativo (preprimaria, primaria, basico, diversificado). "
            "`sequence` define el orden pedagogico y es unico por institucion."
        ),
        tags=CATALOGUE,
        request=LevelCreateSerializer,
        responses={201: LevelSerializer},
    )
    def post(self, request):
        institution = self.institution
        payload = self.validated(LevelCreateSerializer, request)
        level = services.create_level(institution=institution, actor=request.user, **payload)
        return Response(
            LevelSerializer(queries.level_or_404(institution, level.public_id)).data,
            status=status.HTTP_201_CREATED,
        )


class LevelDetailView(CatalogueView):
    serializer_class = LevelSerializer

    @extend_schema(summary="Consultar nivel", tags=CATALOGUE, responses={200: LevelSerializer})
    def get(self, request, public_id):
        return Response(LevelSerializer(queries.level_or_404(self.institution, public_id)).data)

    @extend_schema(
        summary="Actualizar nivel",
        tags=CATALOGUE,
        request=LevelUpdateSerializer,
        responses={200: LevelSerializer},
    )
    def patch(self, request, public_id):
        institution = self.institution
        level = queries.level_or_404(institution, public_id)
        payload = self.validated(LevelUpdateSerializer, request)
        services.update_level(level=level, actor=request.user, **payload)
        return Response(LevelSerializer(queries.level_or_404(institution, public_id)).data)

    @extend_schema(
        summary="Desactivar nivel",
        description="Desactiva el nivel y sus grados. Se rechaza si un ciclo abierto los oferta.",
        tags=CATALOGUE,
        responses={204: None},
    )
    def delete(self, request, public_id):
        level = queries.level_or_404(self.institution, public_id)
        services.deactivate_level(level=level, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------- #
# grades ("grados") — always under a level
# --------------------------------------------------------------------------- #


class LevelGradeListCreateView(CatalogueView):
    def get_serializer_class(self):
        return GradeCreateSerializer if self.request.method == "POST" else GradeSerializer

    @extend_schema(
        summary="Listar grados de un nivel",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE],
        responses={200: GradeSerializer(many=True)},
    )
    def get(self, request, public_id):
        level = queries.level_or_404(self.institution, public_id)
        return Response(GradeSerializer(queries.grades(level, request), many=True).data)

    @extend_schema(
        summary="Crear grado en un nivel",
        description="El codigo del grado es unico en toda la institucion.",
        tags=CATALOGUE,
        request=GradeCreateSerializer,
        responses={201: GradeSerializer},
    )
    def post(self, request, public_id):
        level = queries.level_or_404(self.institution, public_id)
        payload = self.validated(GradeCreateSerializer, request)
        grade = services.create_grade(level=level, actor=request.user, **payload)
        return Response(GradeSerializer(grade).data, status=status.HTTP_201_CREATED)


class GradeDetailView(CatalogueView):
    serializer_class = GradeSerializer

    @extend_schema(summary="Consultar grado", tags=CATALOGUE, responses={200: GradeSerializer})
    def get(self, request, public_id):
        return Response(GradeSerializer(queries.grade_or_404(self.institution, public_id)).data)

    @extend_schema(
        summary="Actualizar grado",
        tags=CATALOGUE,
        request=GradeUpdateSerializer,
        responses={200: GradeSerializer},
    )
    def patch(self, request, public_id):
        grade = queries.grade_or_404(self.institution, public_id)
        payload = self.validated(GradeUpdateSerializer, request)
        services.update_grade(grade=grade, actor=request.user, **payload)
        return Response(GradeSerializer(grade).data)

    @extend_schema(
        summary="Desactivar grado",
        description="Se rechaza si el grado esta ofertado en un ciclo no cerrado.",
        tags=CATALOGUE,
        responses={204: None},
    )
    def delete(self, request, public_id):
        grade = queries.grade_or_404(self.institution, public_id)
        services.deactivate_grade(grade=grade, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------- #
# subjects ("cursos")
# --------------------------------------------------------------------------- #


class SubjectListCreateView(CatalogueView):
    def get_serializer_class(self):
        return SubjectCreateSerializer if self.request.method == "POST" else SubjectSerializer

    @extend_schema(
        summary="Listar cursos",
        description="Cursos de la institucion, con los niveles en los que se imparten.",
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE],
        responses={200: SubjectSerializer(many=True)},
    )
    def get(self, request):
        return Response(
            SubjectSerializer(queries.subjects(self.institution, request), many=True).data
        )

    @extend_schema(
        summary="Crear curso",
        tags=CATALOGUE,
        request=SubjectCreateSerializer,
        responses={201: SubjectSerializer},
    )
    def post(self, request):
        payload = self.validated(SubjectCreateSerializer, request)
        subject = services.create_subject(
            institution=self.institution, actor=request.user, **payload
        )
        return Response(SubjectSerializer(subject).data, status=status.HTTP_201_CREATED)


class SubjectDetailView(CatalogueView):
    serializer_class = SubjectSerializer

    @extend_schema(summary="Consultar curso", tags=CATALOGUE, responses={200: SubjectSerializer})
    def get(self, request, public_id):
        return Response(SubjectSerializer(queries.subject_or_404(self.institution, public_id)).data)

    @extend_schema(
        summary="Actualizar curso",
        tags=CATALOGUE,
        request=SubjectUpdateSerializer,
        responses={200: SubjectSerializer},
    )
    def patch(self, request, public_id):
        subject = queries.subject_or_404(self.institution, public_id)
        payload = self.validated(SubjectUpdateSerializer, request)
        services.update_subject(subject=subject, actor=request.user, **payload)
        return Response(SubjectSerializer(subject).data)

    @extend_schema(
        summary="Desactivar curso",
        description="Los vinculos con niveles se conservan como historia.",
        tags=CATALOGUE,
        responses={204: None},
    )
    def delete(self, request, public_id):
        subject = queries.subject_or_404(self.institution, public_id)
        services.deactivate_subject(subject=subject, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------- #
# level <-> subject links
# --------------------------------------------------------------------------- #


class LevelSubjectListCreateView(CatalogueView):
    def get_serializer_class(self):
        if self.request.method == "POST":
            return LevelSubjectCreateSerializer
        return LevelSubjectSerializer

    @extend_schema(
        summary="Listar cursos de un nivel",
        description="Cursos vinculados al nivel, con obligatoriedad y carga horaria.",
        tags=CATALOGUE,
        responses={200: LevelSubjectSerializer(many=True)},
    )
    def get(self, request, public_id):
        level = queries.level_or_404(self.institution, public_id)
        return Response(LevelSubjectSerializer(queries.level_subjects(level), many=True).data)

    @extend_schema(
        summary="Vincular curso a un nivel",
        description=(
            "Declara que un curso se imparte en el nivel. Nivel y curso deben pertenecer "
            "a la misma institucion. `weekly_hours=0` significa sin definir."
        ),
        tags=CATALOGUE,
        request=LevelSubjectCreateSerializer,
        responses={201: LevelSubjectSerializer},
    )
    def post(self, request, public_id):
        institution = self.institution
        level = queries.level_or_404(institution, public_id)
        payload = self.validated(LevelSubjectCreateSerializer, request)
        subject = _resolve_subject(payload.pop("subject_id"))
        link = services.link_subject_to_level(
            level=level, subject=subject, actor=request.user, **payload
        )
        return Response(LevelSubjectSerializer(link).data, status=status.HTTP_201_CREATED)


class LevelSubjectDetailView(CatalogueView):
    serializer_class = LevelSubjectSerializer

    @extend_schema(
        summary="Actualizar el vinculo curso-nivel",
        tags=CATALOGUE,
        request=LevelSubjectUpdateSerializer,
        responses={200: LevelSubjectSerializer},
    )
    def patch(self, request, public_id, subject_public_id):
        institution = self.institution
        level = queries.level_or_404(institution, public_id)
        subject = queries.subject_or_404(institution, subject_public_id)
        payload = self.validated(LevelSubjectUpdateSerializer, request)
        link = services.update_level_subject(
            level=level, subject=subject, actor=request.user, **payload
        )
        return Response(LevelSubjectSerializer(link).data)

    @extend_schema(
        summary="Desvincular curso de un nivel",
        tags=CATALOGUE,
        responses={204: None},
    )
    def delete(self, request, public_id, subject_public_id):
        institution = self.institution
        level = queries.level_or_404(institution, public_id)
        subject = queries.subject_or_404(institution, subject_public_id)
        services.unlink_subject_from_level(level=level, subject=subject, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------- #
# cycles
# --------------------------------------------------------------------------- #


class AcademicCycleListCreateView(CatalogueView):
    def get_serializer_class(self):
        if self.request.method == "POST":
            return AcademicCycleCreateSerializer
        return AcademicCycleListSerializer

    @extend_schema(
        summary="Listar ciclos escolares",
        tags=CYCLES,
        responses={200: AcademicCycleListSerializer(many=True)},
    )
    def get(self, request):
        cycles = AcademicCycle.objects.filter(institution=self.institution).order_by("-starts_on")
        return Response(AcademicCycleListSerializer(cycles, many=True).data)

    @extend_schema(
        summary="Crear ciclo en borrador",
        tags=CYCLES,
        request=AcademicCycleCreateSerializer,
        responses={201: AcademicCycleListSerializer},
    )
    def post(self, request):
        payload = self.validated(AcademicCycleCreateSerializer, request)
        cycle = AcademicCycle.objects.create(
            institution=self.institution,
            status=AcademicCycle.CycleStatus.DRAFT,
            **payload,
        )
        return Response(AcademicCycleListSerializer(cycle).data, status=status.HTTP_201_CREATED)


class AcademicCycleDetailView(CatalogueView):
    serializer_class = AcademicCycleDetailSerializer

    @extend_schema(
        summary="Consultar ciclo con sus secciones y ocupacion",
        tags=CYCLES,
        responses={200: AcademicCycleDetailSerializer},
    )
    def get(self, request, public_id):
        cycle = queries.cycle_or_404(self.institution, public_id)
        data = AcademicCycleDetailSerializer(cycle).data
        data["sections"] = SectionSerializer(queries.sections(cycle=cycle), many=True).data
        return Response(data)


class AcademicCycleOpenView(CatalogueView):
    serializer_class = AcademicCycleListSerializer

    @extend_schema(
        summary="Abrir ciclo",
        description="Pasa el ciclo de borrador a activo (RF-CIC-003).",
        tags=CYCLES,
        request=None,
        responses={200: AcademicCycleListSerializer},
    )
    def post(self, request, public_id):
        cycle = queries.cycle_or_404(self.institution, public_id)
        services.open_cycle(cycle=cycle, actor=request.user)
        return Response(AcademicCycleListSerializer(cycle).data)


class AcademicCycleCloseView(CatalogueView):
    serializer_class = AcademicCycleListSerializer

    @extend_schema(
        summary="Cerrar ciclo",
        description="Pasa el ciclo de activo a cerrado y congela su estructura (RF-CIC-004).",
        tags=CYCLES,
        request=None,
        responses={200: AcademicCycleListSerializer},
    )
    def post(self, request, public_id):
        cycle = queries.cycle_or_404(self.institution, public_id)
        services.close_cycle(cycle=cycle, actor=request.user)
        return Response(AcademicCycleListSerializer(cycle).data)


# --------------------------------------------------------------------------- #
# grade offerings — the catalogue enrolments are assigned to
# --------------------------------------------------------------------------- #


class CycleOfferingListCreateView(CatalogueView):
    OFFERING_FILTERS = (
        ("campus", "shift__campus__public_id"),
        ("shift", "shift__public_id"),
        ("level", "grade__level__public_id"),
        ("grade", "grade__public_id"),
    )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return GradeOfferingCreateSerializer
        return GradeOfferingSerializer

    @extend_schema(
        summary="Listar la oferta de grados del ciclo",
        description=(
            "Cada elemento es un grado ofertado en una jornada de una sede. "
            "Los filtros aceptan public IDs; un ID inexistente devuelve una lista vacia."
        ),
        tags=CYCLES,
        parameters=[
            OpenApiParameter("campus", str, description="Filtra por sede."),
            OpenApiParameter("shift", str, description="Filtra por jornada."),
            OpenApiParameter("level", str, description="Filtra por nivel."),
            OpenApiParameter("grade", str, description="Filtra por grado."),
        ],
        responses={200: GradeOfferingSerializer(many=True)},
    )
    def get(self, request, cycle_public_id):
        cycle = queries.cycle_or_404(self.institution, cycle_public_id)
        queryset = queries.offerings(cycle)

        for param, lookup in self.OFFERING_FILTERS:
            value = request.query_params.get(param)
            if value:
                queryset = queryset.filter(**{lookup: value})

        return Response(GradeOfferingSerializer(queryset, many=True).data)

    @extend_schema(
        summary="Ofertar un grado en una jornada",
        description=(
            "Agrega un grado a la oferta del ciclo. La jornada determina la sede. "
            "Se rechaza si el ciclo esta cerrado, si hay mezcla de instituciones, "
            "si algun elemento esta inactivo o si la combinacion ya existe."
        ),
        tags=CYCLES,
        request=GradeOfferingCreateSerializer,
        responses={201: GradeOfferingSerializer},
    )
    def post(self, request, cycle_public_id):
        institution = self.institution
        cycle = queries.cycle_or_404(institution, cycle_public_id)
        payload = self.validated(GradeOfferingCreateSerializer, request)

        grade = _resolve_or_domain_error(
            Grade.objects.select_related("level"), payload["grade_id"], "Grade"
        )
        shift = _resolve_or_domain_error(
            Shift.objects.select_related("campus"), payload["shift_id"], "Shift"
        )

        offering = services.create_grade_offering(
            cycle=cycle, shift=shift, grade=grade, actor=request.user
        )
        return Response(
            GradeOfferingSerializer(queries.offering_or_404(institution, offering.public_id)).data,
            status=status.HTTP_201_CREATED,
        )


class GradeOfferingDetailView(CatalogueView):
    serializer_class = GradeOfferingSerializer

    @extend_schema(
        summary="Consultar una oferta de grado",
        tags=CYCLES,
        responses={200: GradeOfferingSerializer},
    )
    def get(self, request, public_id):
        return Response(
            GradeOfferingSerializer(queries.offering_or_404(self.institution, public_id)).data
        )

    @extend_schema(
        summary="Quitar una oferta de grado",
        description="Se rechaza si el ciclo esta cerrado o si la oferta aun tiene secciones.",
        tags=CYCLES,
        responses={204: None},
    )
    def delete(self, request, public_id):
        offering = queries.offering_or_404(self.institution, public_id)
        services.remove_grade_offering(offering=offering, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------- #
# sections
# --------------------------------------------------------------------------- #


class OfferingSectionListCreateView(CatalogueView):
    def get_serializer_class(self):
        return SectionCreateSerializer if self.request.method == "POST" else SectionSerializer

    @extend_schema(
        summary="Listar secciones de una oferta",
        description="Incluye ocupacion activa y cupos libres (RF-EST-008).",
        tags=CYCLES,
        parameters=[INCLUDE_INACTIVE],
        responses={200: SectionSerializer(many=True)},
    )
    def get(self, request, public_id):
        offering = queries.offering_or_404(self.institution, public_id)
        queryset = queries.sections(request, offering=offering)
        return Response(SectionSerializer(queryset, many=True).data)

    @extend_schema(
        summary="Crear seccion en una oferta",
        description="El nombre se normaliza a mayusculas y es unico dentro de la oferta.",
        tags=CYCLES,
        request=SectionCreateSerializer,
        responses={201: SectionSerializer},
    )
    def post(self, request, public_id):
        institution = self.institution
        offering = queries.offering_or_404(institution, public_id)
        payload = self.validated(SectionCreateSerializer, request)
        section = services.create_section(offering=offering, actor=request.user, **payload)
        return Response(
            SectionSerializer(queries.section_or_404(institution, section.public_id)).data,
            status=status.HTTP_201_CREATED,
        )


class SectionDetailView(CatalogueView):
    serializer_class = SectionSerializer

    @extend_schema(summary="Consultar seccion", tags=CYCLES, responses={200: SectionSerializer})
    def get(self, request, public_id):
        return Response(SectionSerializer(queries.section_or_404(self.institution, public_id)).data)

    @extend_schema(
        summary="Actualizar seccion",
        description="La capacidad no puede quedar por debajo de la ocupacion actual.",
        tags=CYCLES,
        request=SectionUpdateSerializer,
        responses={200: SectionSerializer},
    )
    def patch(self, request, public_id):
        institution = self.institution
        section = queries.section_or_404(institution, public_id)
        payload = self.validated(SectionUpdateSerializer, request)
        services.update_section(section=section, actor=request.user, **payload)
        return Response(SectionSerializer(queries.section_or_404(institution, public_id)).data)

    @extend_schema(
        summary="Desactivar seccion",
        description="Se rechaza mientras la seccion tenga matriculas activas.",
        tags=CYCLES,
        responses={204: None},
    )
    def delete(self, request, public_id):
        section = queries.section_or_404(self.institution, public_id)
        services.deactivate_section(section=section, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _resolve_or_domain_error(queryset, public_id, label):
    """
    Resolve a body reference. A bad reference in a payload is a bad request, not
    a missing endpoint, so it raises ``DomainError`` and lands as a 400.
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
    return _resolve_or_domain_error(Subject.objects.all(), public_id, "Subject")
