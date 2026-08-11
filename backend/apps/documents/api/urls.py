from django.urls import path

from .views import DocumentTemplateDetailView, DocumentTemplateListCreateView

urlpatterns = [
    path(
        "templates/", DocumentTemplateListCreateView.as_view(), name="document-template-list-create"
    ),
    path(
        "templates/<uuid:public_id>/",
        DocumentTemplateDetailView.as_view(),
        name="document-template-detail",
    ),
]
