from django.urls import path

from apps.audit.api.views import (
    AuditEventExportView,
    AuditEventListView,
    DataRetentionDeclarationView,
)

urlpatterns = [
    path("events/", AuditEventListView.as_view(), name="audit-event-list"),
    path("events/export/", AuditEventExportView.as_view(), name="audit-event-export"),
    path(
        "retention-declarations/",
        DataRetentionDeclarationView.as_view(),
        name="audit-retention-declaration-create",
    ),
]
