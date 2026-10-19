import pytest
from importlib import import_module
from types import SimpleNamespace
from django.apps import apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from tests.factories.academic import InstitutionFactory
from tests.factories.documents import DocumentTemplateFactory


@pytest.mark.migration
@pytest.mark.django_db
def test_reverse_guard_requires_explicit_resolution_of_legacy_kind_conflicts():
    first = DocumentTemplateFactory()
    second = DocumentTemplateFactory(institution=first.institution, document_kind=first.document_kind)
    guard = import_module("apps.documents.migrations.0016_template_issuance_use").require_legacy_compatibility
    with pytest.raises(RuntimeError, match="desactive"):
        guard(apps, SimpleNamespace(connection=connection))
    second.is_active = False
    second.save(update_fields=["is_active"])
    guard(apps, SimpleNamespace(connection=connection))
    assert first.versions.count() == 0
    assert second.__class__.objects.filter(pk=second.pk).exists()


@pytest.mark.migration
@pytest.mark.postgres
@pytest.mark.django_db(transaction=True)
def test_legacy_templates_migrate_without_rewriting_historical_content():
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    old_target = [("documents", "0015_documentissuance")]
    executor.migrate(old_target)
    old = executor.loader.project_state(old_target).apps
    institution = InstitutionFactory()
    Kind = old.get_model("documents", "DocumentKind")
    Template = old.get_model("documents", "DocumentTemplate")
    Version = old.get_model("documents", "DocumentTemplateVersion")
    originals = []
    try:
        for index, (code, active, expected) in enumerate(
            [
                ("constancia", True, "enrolment_certificate"),
                ("certificate", True, "study_certificate"),
                ("report", True, "none"),
                ("certificate", False, "none"),
            ]
        ):
            kind, _ = Kind.objects.get_or_create(
                institution_id=institution.pk, code=code, defaults={"label": code}
            )
            template = Template.objects.create(
                institution_id=institution.pk,
                document_kind=kind,
                name=f"Legacy {index}",
                code=f"LEG-{index}",
                content="Original {{student.code}}",
                is_active=active,
            )
            version = Version.objects.create(
                template=template,
                sequence=1,
                name=template.name,
                kind=code,
                content=template.content,
            )
            originals.append(
                (template.pk, version.pk, expected, template.content, version.created_at)
            )
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        new = executor.loader.project_state(latest).apps
        for template_id, version_id, expected, content, created_at in originals:
            template = new.get_model("documents", "DocumentTemplate").objects.get(pk=template_id)
            version = new.get_model("documents", "DocumentTemplateVersion").objects.get(
                pk=version_id
            )
            assert template.issuance_use == expected
            assert template.content == version.content == content
            assert version.sequence == 1 and version.created_at == created_at
            assert version.kind in {"constancia", "certificate", "report"}
    finally:
        MigrationExecutor(connection).migrate(latest)
