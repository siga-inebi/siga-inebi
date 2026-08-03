"""
Introduce the academic catalogue: campuses ("sedes"), levels ("niveles"),
grades bound to a level, subjects linked to levels, and grade offerings
(grade + shift of a campus, per cycle) that sections now hang from.

The new foreign keys are non-nullable on purpose: this project has no
production data yet, and silently backfilling structural relations would
invent an academic structure nobody declared. If a database already holds
rows in academics_shift / academics_grade / academics_section, this migration
fails loudly instead.
"""

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("academics", "0001_initial"),
    ]

    operations = [
        # ---------------------------------------------------------------- #
        # drop the uniqueness rules that reference fields about to move
        # ---------------------------------------------------------------- #
        migrations.AlterUniqueTogether(name="shift", unique_together=set()),
        migrations.AlterUniqueTogether(name="grade", unique_together=set()),
        migrations.AlterUniqueTogether(name="section", unique_together=set()),
        migrations.AlterUniqueTogether(name="subject", unique_together=set()),
        # ---------------------------------------------------------------- #
        # new catalogue roots
        # ---------------------------------------------------------------- #
        migrations.CreateModel(
            name="Campus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("name", models.CharField(max_length=150)),
                ("code", models.CharField(max_length=30)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("is_main", models.BooleanField(default=False)),
                (
                    "institution",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="campuses",
                        to="academics.institution",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "campuses",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Level",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("name", models.CharField(max_length=100)),
                ("code", models.CharField(max_length=30)),
                ("sequence", models.PositiveIntegerField()),
                (
                    "institution",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="levels",
                        to="academics.institution",
                    ),
                ),
            ],
            options={"ordering": ["sequence", "name"]},
        ),
        # ---------------------------------------------------------------- #
        # shifts move from the institution to a campus
        # ---------------------------------------------------------------- #
        migrations.RemoveField(model_name="shift", name="institution"),
        migrations.AddField(
            model_name="shift",
            name="campus",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="shifts",
                to="academics.campus",
            ),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="shift", options={"ordering": ["campus__name", "name"]}
        ),
        # ---------------------------------------------------------------- #
        # grades move from the institution to a level and gain an order
        # ---------------------------------------------------------------- #
        migrations.RemoveField(model_name="grade", name="institution"),
        migrations.AddField(
            model_name="grade",
            name="level",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="grades",
                to="academics.level",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="grade",
            name="sequence",
            field=models.PositiveIntegerField(),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="grade",
            options={"ordering": ["level__sequence", "sequence", "name"]},
        ),
        # ---------------------------------------------------------------- #
        # subjects linked to levels
        # ---------------------------------------------------------------- #
        migrations.CreateModel(
            name="LevelSubject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("is_required", models.BooleanField(default=True)),
                ("weekly_hours", models.PositiveIntegerField(default=0)),
                (
                    "level",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="level_subjects",
                        to="academics.level",
                    ),
                ),
                (
                    "subject",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="level_subjects",
                        to="academics.subject",
                    ),
                ),
            ],
            options={"ordering": ["level__sequence", "subject__name"]},
        ),
        migrations.AddField(
            model_name="subject",
            name="levels",
            field=models.ManyToManyField(
                blank=True,
                related_name="subjects",
                through="academics.LevelSubject",
                to="academics.level",
            ),
        ),
        migrations.AlterModelOptions(name="subject", options={"ordering": ["name"]}),
        # ---------------------------------------------------------------- #
        # grade offerings, and sections hanging from them
        # ---------------------------------------------------------------- #
        migrations.CreateModel(
            name="GradeOffering",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "academic_cycle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="grade_offerings",
                        to="academics.academiccycle",
                    ),
                ),
                (
                    "grade",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="offerings",
                        to="academics.grade",
                    ),
                ),
                (
                    "shift",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="grade_offerings",
                        to="academics.shift",
                    ),
                ),
            ],
            options={
                "ordering": [
                    "shift__campus__name",
                    "grade__level__sequence",
                    "grade__sequence",
                ]
            },
        ),
        migrations.RemoveField(model_name="section", name="academic_cycle"),
        migrations.RemoveField(model_name="section", name="grade"),
        migrations.RemoveField(model_name="section", name="shift"),
        migrations.AddField(
            model_name="section",
            name="offering",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sections",
                to="academics.gradeoffering",
            ),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name="section",
            options={
                "ordering": [
                    "offering__grade__level__sequence",
                    "offering__grade__sequence",
                    "name",
                ]
            },
        ),
        # ---------------------------------------------------------------- #
        # uniqueness rules, expressed as named constraints
        # ---------------------------------------------------------------- #
        migrations.AddConstraint(
            model_name="campus",
            constraint=models.UniqueConstraint(
                fields=("institution", "code"), name="unique_campus_code_per_institution"
            ),
        ),
        migrations.AddConstraint(
            model_name="level",
            constraint=models.UniqueConstraint(
                fields=("institution", "code"), name="unique_level_code_per_institution"
            ),
        ),
        migrations.AddConstraint(
            model_name="level",
            constraint=models.UniqueConstraint(
                fields=("institution", "sequence"),
                name="unique_level_sequence_per_institution",
            ),
        ),
        migrations.AddConstraint(
            model_name="shift",
            constraint=models.UniqueConstraint(
                fields=("campus", "code"), name="unique_shift_code_per_campus"
            ),
        ),
        migrations.AddConstraint(
            model_name="grade",
            constraint=models.UniqueConstraint(
                fields=("level", "sequence"), name="unique_grade_sequence_per_level"
            ),
        ),
        migrations.AddConstraint(
            model_name="subject",
            constraint=models.UniqueConstraint(
                fields=("institution", "code"), name="unique_subject_code_per_institution"
            ),
        ),
        migrations.AddConstraint(
            model_name="levelsubject",
            constraint=models.UniqueConstraint(
                fields=("level", "subject"), name="unique_subject_per_level"
            ),
        ),
        migrations.AddConstraint(
            model_name="gradeoffering",
            constraint=models.UniqueConstraint(
                fields=("academic_cycle", "shift", "grade"),
                name="unique_grade_offering_per_cycle_shift",
            ),
        ),
        migrations.AddConstraint(
            model_name="section",
            constraint=models.UniqueConstraint(
                fields=("offering", "name"), name="unique_section_name_per_offering"
            ),
        ),
    ]
