from django.urls import path

from .views import (
    DocumentTemplateDetailView,
    DocumentTemplateListCreateView,
    DocumentTemplateVersionListView,
    DocumentTypeListView,
    FieldTagListView,
    OfficialDocumentEligibilityView,
)

urlpatterns = [
    path(
        "templates/", DocumentTemplateListCreateView.as_view(), name="document-template-list-create"
    ),
    path(
        "templates/<uuid:public_id>/",
        DocumentTemplateDetailView.as_view(),
        name="document-template-detail",
    ),
    path(
        "templates/<uuid:public_id>/versions/",
        DocumentTemplateVersionListView.as_view(),
        name="document-template-version-list",
    ),
    path("field-tags/", FieldTagListView.as_view(), name="document-field-tag-list"),
    path("types/", DocumentTypeListView.as_view(), name="document-type-list"),
    path(
        "official-issuance/eligibility/",
        OfficialDocumentEligibilityView.as_view(),
        name="document-official-issuance-eligibility",
    ),
]
