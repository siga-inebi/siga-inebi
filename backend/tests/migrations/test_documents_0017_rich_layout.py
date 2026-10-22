import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from tests.factories.academic import InstitutionFactory


@pytest.mark.migration
@pytest.mark.postgres
@pytest.mark.django_db(transaction=True)
def test_legacy_plain_template_and_version_keep_content_with_layout_defaults():
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    old_target = [("documents", "0016_template_issuance_use")]
    executor.migrate(old_target)
    old = executor.loader.project_state(old_target).apps
    institution = InstitutionFactory()
    Kind = old.get_model("documents", "DocumentKind")
    Template = old.get_model("documents", "DocumentTemplate")
    Version = old.get_model("documents", "DocumentTemplateVersion")
    content = "Constancia histórica para {{student.full_name}}"

    try:
        kind = Kind.objects.create(
            institution_id=institution.pk,
            code="constancia-historica",
            label="Constancia histórica",
        )
        template = Template.objects.create(
            institution_id=institution.pk,
            document_kind=kind,
            name="Plantilla histórica",
            code="HIST",
            content=content,
        )
        version = Version.objects.create(
            template=template,
            sequence=1,
            name=template.name,
            kind=kind.code,
            content=content,
        )

        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        new = executor.loader.project_state(latest).apps
        migrated_template = new.get_model("documents", "DocumentTemplate").objects.get(
            pk=template.pk
        )
        migrated_version = new.get_model("documents", "DocumentTemplateVersion").objects.get(
            pk=version.pk
        )

        for migrated in (migrated_template, migrated_version):
            assert migrated.content == content
            assert migrated.content_format == "plain"
            assert migrated.page_size == "letter"
            assert migrated.orientation == "portrait"
            assert migrated.margin_top == 54
            assert migrated.margin_right == 54
            assert migrated.margin_bottom == 54
            assert migrated.margin_left == 54
            assert migrated.footer_text == ""
            assert migrated.signature_blocks == []
    finally:
        MigrationExecutor(connection).migrate(latest)
