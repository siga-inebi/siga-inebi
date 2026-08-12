from django.db import models

from apps.common.models import TimeStampedModel


class DocumentTemplate(TimeStampedModel):
    """
    Catalogue entry for a document template ("plantilla"): a reusable format
    or structure used to issue reports and certificates (RF-PLA-001).
    """

    class TemplateKind(models.TextChoices):
        CERTIFICATE = "certificate", "Certificado"
        REPORT = "report", "Reporte"
        OTHER = "other", "Otro"

    institution = models.ForeignKey(
        "academics.Institution", on_delete=models.CASCADE, related_name="document_templates"
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30)
    kind = models.CharField(max_length=20, choices=TemplateKind.choices, default=TemplateKind.OTHER)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"], name="unique_document_template_code_per_institution"
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def institutional_header(self):
        """
        Mandatory institutional header every print template carries by default
        (RF-PLA-004). Derived from the institution, never stored or
        configurable per template, so it always reflects current
        institutional data and can never be turned off.

        ``logo_url`` is ``None`` until the ``file-storage`` domain exists
        (``docs/architecture/file-storage-strategy.md``); ``Institution`` has
        no logo field yet.
        """
        return {
            "institution_name": self.institution.name,
            "institution_short_name": self.institution.short_name,
            "logo_url": None,
        }


class DocumentTemplateVersion(TimeStampedModel):
    """
    Immutable snapshot of a document template's content at a point in time
    (RF-PLA-005), for institutional traceability. Written only by
    ``apps.documents.services`` on creation and content updates; never
    edited or deleted, same guarantee as ``apps.audit.models.AuditEvent``.
    """

    template = models.ForeignKey(
        DocumentTemplate, on_delete=models.CASCADE, related_name="versions"
    )
    sequence = models.PositiveIntegerField()
    name = models.CharField(max_length=150)
    kind = models.CharField(max_length=20, choices=DocumentTemplate.TemplateKind.choices)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "sequence"], name="unique_document_template_version_sequence"
            ),
        ]

    def __str__(self):
        return f"{self.template.name} v{self.sequence}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise RuntimeError("Document template versions cannot be modified.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Document template versions cannot be deleted.")
