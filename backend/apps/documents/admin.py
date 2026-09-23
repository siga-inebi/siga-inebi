from django.contrib import admin

from apps.documents.models import (
    DocumentKind,
    DocumentRecord,
    DocumentTemplate,
    DocumentTemplateVersion,
)

admin.site.register(DocumentKind)
admin.site.register(DocumentTemplate)
admin.site.register(DocumentTemplateVersion)
admin.site.register(DocumentRecord)
