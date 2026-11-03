"""
RF-DOC-001: adding the teacher owner must not touch documents already stored.

Every existing record belongs to a student; after the migration it must still
point at the same student, with no teacher, and satisfy the new constraints.
"""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from tests.factories.students import StudentFactory


def migrate_to(target):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(target)
    return executor.loader.project_state(target).apps


@pytest.mark.migration
@pytest.mark.postgres
@pytest.mark.django_db(transaction=True)
def test_documents_0014_keeps_existing_student_records_intact():
    """RF-DOC-001: the migration is additive for stored student documents."""
    old_apps = migrate_to([("documents", "0013_documentkind")])

    DocumentRecord = old_apps.get_model("documents", "DocumentRecord")

    # Only ``documents`` is rolled back; the student tables keep their current
    # schema, so the current factory is the faithful way to create the owner.
    student = StudentFactory()
    record = DocumentRecord.objects.create(
        student_id=student.pk,
        filename="acta.pdf",
        storage_key="local/migration-0014-acta.pdf",
        content_type="application/pdf",
        size_bytes=10,
        checksum="abc",
    )

    new_apps = migrate_to([("documents", "0014_documentrecord_teacher_owner")])

    migrated = new_apps.get_model("documents", "DocumentRecord").objects.get(pk=record.pk)
    assert migrated.student_id == student.pk
    assert migrated.teacher_id is None
    assert migrated.checksum == "abc"
    assert migrated.version_number == 1

    # Leave the schema where the rest of the session expects it.
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    migrate_to([node for node in executor.loader.graph.leaf_nodes() if node[0] == "documents"])
