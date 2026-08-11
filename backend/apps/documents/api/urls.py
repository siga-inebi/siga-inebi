from django.urls import path

from .views import (
    DocumentTemplateDetailView,
    DocumentTemplateListCreateView,
    DocumentTemplateVersionListView,
    FieldTagListView,
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
]
