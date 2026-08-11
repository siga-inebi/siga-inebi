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
