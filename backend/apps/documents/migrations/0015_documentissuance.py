"""
RF-EMI-001: immutable register of individually issued constancias and
certificados. New table only; it stores metadata (folio, verification code,
template version, SHA-256, size), never the generated PDF (RF-DOC-008).
"""

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0014_documentrecord_teacher_owner"),
        ("enrolments", "0007_studentmovementannulment"),
        ("students", "0007_add_transferred_student_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentIssuance",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "document_type",
                    models.CharField(
                        choices=[
                            ("enrolment_certificate", "Constancia de inscripcion"),
                            ("study_certificate", "Certificado de estudios"),
                        ],
                        max_length=40,
                    ),
                ),
                ("folio", models.CharField(max_length=100)),
                ("verification_code", models.CharField(max_length=64, unique=True)),
                ("checksum", models.CharField(max_length=64)),
                ("size_bytes", models.PositiveIntegerField()),
                ("issued_at", models.DateTimeField()),
                (
                    "enrolment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="document_issuances",
                        to="enrolments.enrolment",
                    ),
                ),
                (
                    "issued_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="document_issuances",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="document_issuances",
                        to="students.student",
                    ),
                ),
                (
                    "template_version",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="issuances",
                        to="documents.documenttemplateversion",
                    ),
                ),
            ],
            options={
                "ordering": ["-issued_at", "-pk"],
            },
        ),
    ]
