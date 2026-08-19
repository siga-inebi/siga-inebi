from django.contrib import admin

from apps.documents.models import DocumentRecord, DocumentTemplate, DocumentTemplateVersion

admin.site.register(DocumentTemplate)
admin.site.register(DocumentTemplateVersion)
admin.site.register(DocumentRecord)
