import re
import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class DocumentRecordQuerySet(models.QuerySet):
    """Preserve document metadata and history: bulk delete is prohibited."""

    def delete(self):
        raise RuntimeError("Document records cannot be deleted.")

    def update(self, **kwargs):
        raise RuntimeError("Document records cannot be modified.")


# Vida de un enlace de descarga (RF-DOC-005).
DOWNLOAD_TOKEN_LIFETIME = timedelta(minutes=5)


def default_download_expiry():
    """
    Vencimiento por defecto de un token de descarga.

    Es una funcion con nombre y no una lambda porque Django tiene que
    SERIALIZARLA en la migracion: una lambda no se puede serializar, asi que
    ``makemigrations --check`` detectaba un cambio pendiente en cada corrida y la
    compuerta de CI quedaba roja sin que nada hubiera cambiado.
    """
    return timezone.now() + DOWNLOAD_TOKEN_LIFETIME


class DocumentRecord(TimeStampedModel):
    """Persisted metadata for stored documents without allowing hard deletes.

    The storage byte content stays outside the database, while the metadata and
    lineage remain auditable and linked to the student's dossier history.
    """

    objects = DocumentRecordQuerySet.as_manager()

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
    version_group_id = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    version_number = models.PositiveIntegerField(default=1)
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="replacement_versions",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=StorageStatus.choices,
        default=StorageStatus.ACTIVE,
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["version_group_id", "version_number"],
                name="unique_document_record_version_in_group",
            ),
        ]

    def __str__(self):
        return self.filename

    def save(self, *args, **kwargs):
        if self.pk:
            original = (
                DocumentRecord.objects.filter(pk=self.pk)
                .values(
                    "student_id",
                    "enrolment_id",
                    "filename",
                    "storage_key",
                    "content_type",
                    "size_bytes",
                    "checksum",
                    "version_group_id",
                    "version_number",
                    "supersedes_id",
                )
                .first()
            )
            if original is not None:
                immutable_fields = {
                    "student_id": self.student_id,
                    "enrolment_id": self.enrolment_id,
                    "filename": self.filename,
                    "storage_key": self.storage_key,
                    "content_type": self.content_type,
                    "size_bytes": self.size_bytes,
                    "checksum": self.checksum,
                    "version_group_id": self.version_group_id,
                    "version_number": self.version_number,
                    "supersedes_id": self.supersedes_id,
                }
                if any(original[field] != value for field, value in immutable_fields.items()):
                    raise RuntimeError(
                        "Document record metadata cannot be modified after creation."
                    )
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
    content = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "code"], name="unique_document_template_code_per_institution"
            ),
            models.UniqueConstraint(
                fields=["institution", "kind"],
                condition=models.Q(is_active=True),
                name="unique_active_document_template_per_kind_per_institution",
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
    content = models.TextField(blank=True, default="")

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


class DocumentDownloadToken(TimeStampedModel):
    """Short-lived token for controlled document downloads (RF-DOC-005)."""

    document = models.ForeignKey(
        DocumentRecord,
        on_delete=models.PROTECT,
        related_name="download_tokens",
    )
    created_by = models.ForeignKey(
        "identity.UserAccount",
        on_delete=models.PROTECT,
        related_name="document_download_tokens",
        null=True,
        blank=True,
    )
    token_hash = models.CharField(max_length=128, unique=True)
    expires_at = models.DateTimeField(default=default_download_expiry)
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_valid(self):
        return (
            self.is_active
            and self.revoked_at is None
            and self.used_at is None
            and self.expires_at > timezone.now()
        )

    def __str__(self):
        return f"Download token for {self.document_id}"


class DocumentDeliveryReceipt(TimeStampedModel):
    """Immutable acknowledgement that a printed document was delivered to a guardian."""

    student = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="document_delivery_receipts",
    )
    guardian = models.ForeignKey(
        "students.Guardian",
        on_delete=models.PROTECT,
        related_name="document_delivery_receipts",
    )
    document_type = models.CharField(max_length=100)
    folio = models.CharField(max_length=100, blank=True)
    recipient_name = models.CharField(max_length=150, blank=True)
    delivered_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-delivered_at", "-created_at"]

    def __str__(self):
        return f"{self.document_type} entregado a {self.guardian_id}"


class OfficialFolio(TimeStampedModel):
    """Institutional counter for the official document folio sequence."""

    institution = models.ForeignKey(
        "academics.Institution",
        on_delete=models.PROTECT,
        related_name="official_folios",
    )
    year = models.PositiveSmallIntegerField()
    sequence = models.PositiveIntegerField()
    document_type = models.CharField(max_length=50, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-year", "-sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "year", "sequence"],
                name="unique_official_folio_per_institution_year_sequence",
            )
        ]

    @property
    def folio_code(self):
        prefix = (self.institution.short_name or self.institution.name or "DOC").strip().upper()
        prefix = re.sub(r"[^A-Z0-9]+", "", prefix) or "DOC"
        return f"{prefix}-{self.year}-{self.sequence:04d}"

    def __str__(self):
        return self.folio_code


class DocumentBatchRun(TimeStampedModel):
    """
    Idempotency marker for a batch emission (RF-EMI-006, ampliado a pedido
    del usuario -- el issue original no lo exige). Reports themselves stay
    ephemeral (never persisted, per ``compile_document_batch``'s contract);
    this only records that a client-identified batch already ran, so a
    retry with the same ``client_batch_id`` is recognised and skipped
    instead of re-emitting the same documents and audit events.
    """

    client_batch_id = models.CharField(max_length=100, blank=True, default="")
    document_type = models.CharField(max_length=100)
    enrolment_count = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["client_batch_id"],
                condition=~models.Q(client_batch_id=""),
                name="unique_document_batch_run_client_batch_id",
            )
        ]

    def __str__(self):
        return self.client_batch_id or f"batch-run-{self.pk}"


class DocumentVerificationCode(TimeStampedModel):
    """
    Public verification record for an emitted document (RF-EMI-009).

    Unlike ``OfficialFolio.folio_code``, ``code`` is a random, unguessable
    token (``secrets.token_urlsafe``), never sequential -- a public lookup
    must not let anyone enumerate issued documents by walking a counter.
    Deliberately carries no student reference: the public endpoint only
    needs to confirm authenticity, and keeping the model minimal means it
    cannot leak more than that even by accident.
    """

    code = models.CharField(max_length=64, unique=True)
    document_type = models.CharField(max_length=100, blank=True)
    issued_at = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        if self.pk:
            raise RuntimeError("Document verification codes cannot be modified.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Document verification codes cannot be deleted.")
