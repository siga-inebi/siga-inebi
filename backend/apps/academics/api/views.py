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

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.academics import services
from apps.academics.api import queries
from apps.academics.models import AcademicCycle, Section, Subject, TeachingAssignment
from apps.common.models import DomainError
from apps.teachers.models import Teacher

from .serializers import (
    AcademicCycleCloneSerializer,
    AcademicCycleCreateSerializer,
    AcademicCycleSerializer,
    CampusCreateSerializer,
    CampusSerializer,
    CampusUpdateSerializer,
    GradeCreateSerializer,
    GradeSerializer,
    GradeUpdateSerializer,
    LevelCreateSerializer,
    LevelSerializer,
    LevelSubjectCreateSerializer,
    LevelSubjectSerializer,
    LevelSubjectUpdateSerializer,
    LevelUpdateSerializer,
    ShiftCreateSerializer,
    ShiftSerializer,
    ShiftUpdateSerializer,
    SubjectCreateSerializer,
    SubjectSerializer,
    SubjectUpdateSerializer,
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

    def require_assignment_scope(self):
        if not self.request.user.has_scoped_permission(
            "scope_assign", scope={"institution": self.institution}
        ):
            raise PermissionDenied("Actor lacks the required permission or institution scope.")


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
        return AcademicCycle.objects.filter(institution=self.institution).order_by(
            "-year", "starts_on"
        )

    def create(self, request, payload):
        return services.create_academic_cycle(
            institution=self.institution,
            actor=request.user,
            **payload,
        )


class AcademicCycleActivateView(CatalogueView):
    @extend_schema(
        summary="Activar ciclo escolar",
        tags=["academics: cycles"],
        request=None,
        responses={200: AcademicCycleSerializer},
    )
    def post(self, request, public_id):
        cycle = get_object_or_404(
            AcademicCycle,
            public_id=public_id,
            institution=self.institution,
        )
        activated = services.activate_academic_cycle(cycle=cycle, actor=request.user)
        return Response(AcademicCycleSerializer(activated).data)


class AcademicCycleCloneView(CatalogueView):
    serializer_class = AcademicCycleCloneSerializer

    @extend_schema(
        summary="Clonar estructura hacia un ciclo nuevo",
        tags=["academics: cycles"],
        request=AcademicCycleCloneSerializer,
        responses={201: AcademicCycleSerializer},
    )
    def post(self, request, public_id):
        source = get_object_or_404(
            AcademicCycle,
            public_id=public_id,
            institution=self.institution,
        )
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
        academic_cycle = _resolve(
            AcademicCycle.objects.all(), payload["academic_cycle_id"], "Academic cycle"
        )
        if academic_cycle.institution_id != self.institution.id:
            raise DomainError("Academic cycle must belong to the current institution.")
        assignment = services.create_teaching_assignment(
            academic_cycle=academic_cycle,
            section=_resolve(Section.objects.all(), payload["section_id"], "Section"),
            subject=_resolve(Subject.objects.all(), payload["subject_id"], "Subject"),
            teacher=_resolve(Teacher.objects.all(), payload["teacher_id"], "Teacher").person,
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
        assignment = _resolve(TeachingAssignment.objects.all(), public_id, "Teaching assignment")
        if assignment.academic_cycle.institution_id != self.institution.id:
            raise DomainError("Teaching assignment must belong to the current institution.")
        successor = services.reassign_teaching_assignment(
            assignment=assignment,
            teacher=_resolve(Teacher.objects.all(), payload["teacher_id"], "Teacher").person,
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
        teacher = (
            _resolve(Teacher.objects.all(), teacher_id, "Teacher").person if teacher_id else None
        )
        academic_cycle = (
            _resolve(AcademicCycle.objects.all(), academic_cycle_id, "Academic cycle")
            if academic_cycle_id
            else None
        )
        page = self.paginate_queryset(
            queries.teaching_assignment_history(
                self.institution, teacher=teacher, academic_cycle=academic_cycle
            )
        )
        return self.get_paginated_response(TeachingAssignmentSerializer(page, many=True).data)


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
