"""
RF-DOC-001: a document record may belong to a teacher's dossier, not only to a
student's.

Safe for existing rows: every record stored so far has a student and no
teacher, which already satisfies both new constraints, so no data step is
needed. ``student`` only becomes nullable; nothing is rewritten or deleted.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("documents", "0013_documentkind"),
        ("enrolments", "0007_studentmovementannulment"),
        ("students", "0007_add_transferred_student_status"),
        ("teachers", "0002_alter_teacher_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="documentrecord",
            name="teacher",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="document_records",
                to="teachers.teacher",
            ),
        ),
        migrations.AlterField(
            model_name="documentrecord",
            name="student",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="document_records",
                to="students.student",
            ),
        ),
        migrations.AddConstraint(
            model_name="documentrecord",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("student__isnull", False), ("teacher__isnull", True)),
                    models.Q(("student__isnull", True), ("teacher__isnull", False)),
                    _connector="OR",
                ),
                name="document_record_has_exactly_one_owner",
            ),
        ),
        migrations.AddConstraint(
            model_name="documentrecord",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("enrolment__isnull", True), ("student__isnull", False), _connector="OR"
                ),
                name="document_record_enrolment_requires_student",
            ),
        ),
    ]
