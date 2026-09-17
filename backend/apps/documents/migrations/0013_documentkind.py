"""
Move the document-type catalogue out of code and into the database (RNF-MAN-001).

Four steps in one file so the database is never left with a template whose type
is unknown:

1. create ``DocumentKind``;
2. add a nullable FK on ``DocumentTemplate``;
3. seed one row per institution for every code already in use (plus the three
   the enum shipped with) and point each template at its row;
4. make the FK mandatory, drop the old ``kind`` column and move the
   "one active template per type" constraint onto the FK.

The version snapshots keep their own ``kind`` column: it is a frozen copy of
the code at the time of the snapshot (RF-PLA-005), not a reference.
"""

import uuid

import django.db.models.deletion
from django.db import migrations, models

SEED_KINDS = (
    ("certificate", "Certificado"),
    ("report", "Reporte"),
    ("other", "Otro"),
)


def seed_kinds_and_link_templates(apps, schema_editor):
    Institution = apps.get_model("academics", "Institution")
    DocumentKind = apps.get_model("documents", "DocumentKind")
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")

    labels = dict(SEED_KINDS)

    for institution in Institution.objects.all():
        used_codes = set(
            DocumentTemplate.objects.filter(institution=institution)
            .values_list("kind", flat=True)
            .distinct()
        )
        codes = [code for code, _label in SEED_KINDS]
        codes += sorted(code for code in used_codes if code and code not in labels)

        by_code = {}
        for code in codes:
            by_code[code], _created = DocumentKind.objects.get_or_create(
                institution=institution,
                code=code,
                defaults={"label": labels.get(code, code), "description": ""},
            )

        for template in DocumentTemplate.objects.filter(institution=institution):
            template.document_kind = by_code[template.kind or "other"]
            template.save(update_fields=["document_kind"])


def unlink_templates(apps, schema_editor):
    DocumentTemplate = apps.get_model("documents", "DocumentTemplate")
    for template in DocumentTemplate.objects.select_related("document_kind"):
        template.kind = template.document_kind.code
        template.save(update_fields=["kind"])


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0001_initial"),
        ("documents", "0012_documentverificationcode_folio"),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentKind",
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
                ("code", models.CharField(max_length=30)),
                ("label", models.CharField(max_length=100)),
                ("description", models.CharField(blank=True, default="", max_length=255)),
                (
                    "institution",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="document_kinds",
                        to="academics.institution",
                    ),
                ),
            ],
            options={"ordering": ["label"]},
        ),
        migrations.AddConstraint(
            model_name="documentkind",
            constraint=models.UniqueConstraint(
                fields=("institution", "code"),
                name="unique_document_kind_code_per_institution",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="documenttemplate",
            name="unique_active_document_template_per_kind_per_institution",
        ),
        migrations.AddField(
            model_name="documenttemplate",
            name="document_kind",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="templates",
                to="documents.documentkind",
            ),
        ),
        migrations.RunPython(seed_kinds_and_link_templates, unlink_templates),
        migrations.AlterField(
            model_name="documenttemplate",
            name="document_kind",
            field=models.ForeignKey(
                help_text="Tipo de documento del catalogo institucional (RNF-MAN-001).",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="templates",
                to="documents.documentkind",
            ),
        ),
        migrations.RemoveField(model_name="documenttemplate", name="kind"),
        migrations.AddConstraint(
            model_name="documenttemplate",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_active", True)),
                fields=("institution", "document_kind"),
                name="unique_active_document_template_per_kind_per_institution",
            ),
        ),
        migrations.AlterField(
            model_name="documenttemplateversion",
            name="kind",
            field=models.CharField(max_length=30),
        ),
    ]
