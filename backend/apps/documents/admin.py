from django.contrib import admin

from apps.documents.models import DocumentTemplate, DocumentTemplateVersion

admin.site.register(DocumentTemplate)
admin.site.register(DocumentTemplateVersion)
