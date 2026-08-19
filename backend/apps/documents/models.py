from django.db import models

from apps.common.models import TimeStampedModel


class DocumentRecord(TimeStampedModel):
    """Persisted metadata for stored documents without allowing hard deletes.

    The storage byte content stays outside the database, while the metadata and
    lineage remain auditable and linked to the student's dossier history.
    """

    class StorageStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"
        RETAINED = "retained", "Retained"

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="document_records",
    )
    enrolment = models.ForeignKey(
        "enrolments.Enrolment",
        on_delete=models.PROTECT,
        related_name="document_records",
        null=True,
        blank=True,
    )
    filename = models.CharField(max_length=255)
    storage_key = models.CharField(max_length=500, unique=True)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveBigIntegerField()
    checksum = models.CharField(max_length=128)
    status = models.CharField(
        max_length=20,
        choices=StorageStatus.choices,
        default=StorageStatus.ACTIVE,
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.filename

    def save(self, *args, **kwargs):
        if self.pk and ("student_id" in self.__dict__ or "enrolment_id" in self.__dict__):
            original = DocumentRecord.objects.filter(pk=self.pk).values_list(
                "student_id", "enrolment_id"
            ).first()
            if original is not None:
                previous_student_id, previous_enrolment_id = original
                current_student_id = self.student_id
                current_enrolment_id = self.enrolment_id
                if (
                    previous_student_id != current_student_id
                    or previous_enrolment_id != current_enrolment_id
                ):
                    raise RuntimeError("Document record links cannot be modified after creation.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Document records cannot be deleted.")


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

    def delete(self, *args, **kwargs):
        raise RuntimeError("Document templates cannot be deleted.")

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
