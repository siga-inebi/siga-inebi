from django.urls import path

from apps.audit.api.views import AuditEventExportView, AuditEventListView

urlpatterns = [
    path("events/", AuditEventListView.as_view(), name="audit-event-list"),
    path("events/export/", AuditEventExportView.as_view(), name="audit-event-export"),
]
