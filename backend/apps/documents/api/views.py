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

from apps.academics.api.views import (
    CatalogueDetailView,
    CatalogueListCreateView,
    DeactivateMixin,
    RetrieveMixin,
    UpdateMixin,
)
from apps.documents import services
from apps.documents.api import queries

from .serializers import (
    DocumentTemplateCreateSerializer,
    DocumentTemplateSerializer,
    DocumentTemplateUpdateSerializer,
)

CATALOGUE = ["documents: catalogue"]

INCLUDE_INACTIVE = OpenApiParameter(
    name="include_inactive",
    type=bool,
    location=OpenApiParameter.QUERY,
    required=False,
    description="Incluye registros desactivados. Por defecto solo se listan los activos.",
)


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
