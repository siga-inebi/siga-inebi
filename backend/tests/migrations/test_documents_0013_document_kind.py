"""
RNF-MAN-001: the document-type catalogue moves from an enum to rows.

The risk this test covers is data, not schema: an institution upgrading with
templates already stored must come out the other side with every template
pointing at a catalogue row carrying the same code, including a code the enum
never had (rows written before an older deploy, or straight into the database).
"""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


def migrate_to(target):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(target)
    return executor.loader.project_state(target).apps


@pytest.mark.migration
@pytest.mark.postgres
@pytest.mark.django_db(transaction=True)
def test_documents_0013_seeds_the_catalogue_and_links_existing_templates():
    old_apps = migrate_to([("documents", "0012_documentverificationcode_folio")])

    Institution = old_apps.get_model("academics", "Institution")
    DocumentTemplate = old_apps.get_model("documents", "DocumentTemplate")

    institution = Institution.objects.create(name="INEBI", short_name="INEBI")
    DocumentTemplate.objects.create(
        institution_id=institution.pk, name="Certificado", code="CERT", kind="certificate"
    )
    DocumentTemplate.objects.create(
        institution_id=institution.pk, name="Constancia", code="CONST", kind="constancia"
    )

    new_apps = migrate_to([("documents", "0013_documentkind")])

    DocumentKind = new_apps.get_model("documents", "DocumentKind")
    DocumentTemplate = new_apps.get_model("documents", "DocumentTemplate")

    kinds = dict(
        DocumentKind.objects.filter(institution_id=institution.pk).values_list("code", "label")
    )

    assert kinds["certificate"] == "Certificado"
    assert kinds["report"] == "Reporte"
    assert kinds["other"] == "Otro"
    # A code the enum never admitted is preserved rather than collapsed into
    # "other": the template documented a real institutional type.
    assert kinds["constancia"] == "constancia"

    certificate = DocumentTemplate.objects.get(code="CERT")
    constancia = DocumentTemplate.objects.get(code="CONST")

    assert certificate.document_kind.code == "certificate"
    assert constancia.document_kind.code == "constancia"

    # Leave the schema where the rest of the session expects it: unapplying
    # migrations is global to the test database, not to this test.
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    migrate_to([node for node in executor.loader.graph.leaf_nodes() if node[0] == "documents"])
