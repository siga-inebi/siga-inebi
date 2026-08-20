"""
HTTP layer for the document templates catalogue.

Views only translate between HTTP and the domain services in
``apps.documents.services``; every invariant lives there. ``DomainError`` is
turned into a 400 envelope by ``config.api.exception_handler``, so no view
catches it (AGENTS.md #8).

The request/response plumbing is shared with the rest of the catalogue-shaped
resources in the repo (``apps.academics.api.views``), so it is reused here
rather than duplicated.
"""

from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from apps.academics.api.views import (
    CatalogueDetailView,
    CatalogueListCreateView,
    CatalogueView,
    DeactivateMixin,
    RetrieveMixin,
    UpdateMixin,
)
from apps.documents import services
from apps.documents.api import queries

from .serializers import (
    DocumentTemplateCreateSerializer,
    DocumentTemplateSerializer,
    DocumentTemplateTypeSerializer,
    DocumentTemplateUpdateSerializer,
    DocumentTemplateVersionSerializer,
    FieldTagSerializer,
    OfficialDocumentEligibilityQuerySerializer,
    OfficialDocumentEligibilityResponseSerializer,
)

CATALOGUE = ["documents: catalogue"]
OFFICIAL_ISSUANCE = ["documents: official issuance"]

INCLUDE_INACTIVE = OpenApiParameter(
    name="include_inactive",
    type=bool,
    location=OpenApiParameter.QUERY,
    required=False,
    description="Incluye registros desactivados. Por defecto solo se listan los activos.",
)

INCLUDE_SENSITIVE = OpenApiParameter(
    name="include_sensitive",
    type=bool,
    location=OpenApiParameter.QUERY,
    required=False,
    description=(
        "Incluye etiquetas sensibles/confidenciales. Requiere el permiso "
        "student.view_sensitive. Excluidas por defecto."
    ),
)

ENROLMENT_ID = OpenApiParameter(
    name="enrolment_id",
    type=str,
    location=OpenApiParameter.QUERY,
    required=True,
    description="Public ID de la matricula que se evalua.",
)


def _wants_sensitive(request):
    return str(request.query_params.get("include_sensitive", "")).lower() in {"1", "true", "yes"}


@extend_schema_view(
    get=extend_schema(
        summary="Listar plantillas",
        description=(
            "Plantillas de documentos de la institucion. Solo activas salvo "
            "`include_inactive=true`."
        ),
        tags=CATALOGUE,
        parameters=[INCLUDE_INACTIVE],
        responses={200: DocumentTemplateSerializer(many=True)},
    ),
    post=extend_schema(
        summary="Crear plantilla",
        description=(
            "Registra una plantilla de documento. El codigo se normaliza a mayusculas "
            "y es unico por institucion."
        ),
        tags=CATALOGUE,
        request=DocumentTemplateCreateSerializer,
        responses={201: DocumentTemplateSerializer},
    ),
)
class DocumentTemplateListCreateView(CatalogueListCreateView):
    list_serializer = DocumentTemplateSerializer
    create_serializer = DocumentTemplateCreateSerializer

    def list_queryset(self, request):
        return queries.document_templates(self.institution, request)

    def create(self, request, payload):
        template = services.create_document_template(
            institution=self.institution, actor=request.user, **payload
        )
        return queries.document_template_or_404(self.institution, template.public_id)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar plantilla", tags=CATALOGUE, responses={200: DocumentTemplateSerializer}
    ),
    patch=extend_schema(
        summary="Actualizar plantilla",
        description="El codigo es inmutable; se actualizan nombre, descripcion y tipo.",
        tags=CATALOGUE,
        request=DocumentTemplateUpdateSerializer,
        responses={200: DocumentTemplateSerializer},
    ),
    delete=extend_schema(
        summary="Desactivar plantilla",
        description="Desactiva la plantilla en lugar de borrarla.",
        tags=CATALOGUE,
        responses={204: None},
    ),
)
class DocumentTemplateDetailView(RetrieveMixin, UpdateMixin, DeactivateMixin, CatalogueDetailView):
    detail_serializer = DocumentTemplateSerializer
    update_serializer = DocumentTemplateUpdateSerializer

    def get_object(self, public_id):
        return queries.document_template_or_404(self.institution, public_id)

    def update(self, request, template, payload):
        services.update_document_template(template=template, actor=request.user, **payload)

    def deactivate(self, request, template):
        services.deactivate_document_template(template=template, actor=request.user)


@extend_schema_view(
    get=extend_schema(
        summary="Historial de versiones de la plantilla",
        description=(
            "Historial inmutable de contenido de la plantilla, mas reciente primero (RF-PLA-005)."
        ),
        tags=CATALOGUE,
        responses={200: DocumentTemplateVersionSerializer(many=True)},
    ),
)
class DocumentTemplateVersionListView(CatalogueView):
    def get(self, request, public_id):
        template = queries.document_template_or_404(self.institution, public_id)
        page = self.paginate_queryset(queries.document_template_versions(template))
        serializer = DocumentTemplateVersionSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


@extend_schema_view(
    get=extend_schema(
        summary="Listar etiquetas dinamicas",
        description=(
            "Catalogo cerrado y predefinido de etiquetas dinamicas disponibles para el "
            "contenido de las plantillas (RF-PLA-002). Las etiquetas sensibles se excluyen "
            "por defecto (RF-PLA-003)."
        ),
        tags=CATALOGUE,
        parameters=[INCLUDE_SENSITIVE],
        responses={200: FieldTagSerializer(many=True)},
    ),
)
class FieldTagListView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FieldTagSerializer

    def get(self, request):
        catalogue = services.list_field_tags(
            actor=request.user, include_sensitive=_wants_sensitive(request)
        )
        tags = [
            {"code": code, "label": label, "sensitive": sensitive}
            for code, label, sensitive in catalogue
        ]
        page = self.paginate_queryset(tags)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


@extend_schema_view(
    get=extend_schema(
        summary="Listar tipos de documento",
        description="Catalogo fijo de tipos de documento soportados por la institucion.",
        tags=CATALOGUE,
        responses={200: DocumentTemplateTypeSerializer(many=True)},
    ),
)
class DocumentTypeListView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DocumentTemplateTypeSerializer

    def get(self, request):
        catalogue = services.list_document_types()
        types = [{"code": code, "label": label} for code, label in catalogue]
        page = self.paginate_queryset(types)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


@extend_schema_view(
    get=extend_schema(
        summary="Consultar elegibilidad de emision oficial",
        description=(
            "Indica si una matricula puede continuar con la emision de un documento oficial. "
            "La emision queda bloqueada mientras existan documentos obligatorios pendientes "
            "(RF-MAT-006)."
        ),
        tags=OFFICIAL_ISSUANCE,
        parameters=[ENROLMENT_ID],
        responses={200: OfficialDocumentEligibilityResponseSerializer},
    ),
)
class OfficialDocumentEligibilityView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = OfficialDocumentEligibilityQuerySerializer

    def get(self, request):
        # The permission is checked before the enrolment is resolved: otherwise a
        # caller without `document_issue` could probe which enrolments exist by
        # telling a 404 apart from a 403.
        services.ensure_official_document_issuance_permission(actor=request.user)
        query = self.get_serializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        enrolment = queries.enrolment_or_404(query.validated_data["enrolment_id"])
        blocking_codes = services.evaluate_official_document_issuance(
            enrolment=enrolment, actor=request.user
        )
        return Response({"eligible": not blocking_codes, "blocking_document_codes": blocking_codes})
