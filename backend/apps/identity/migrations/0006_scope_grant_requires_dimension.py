from django.db import migrations, models


def deactivate_empty_scope_grants(apps, schema_editor):
    ScopeGrant = apps.get_model("identity", "ScopeGrant")
    ScopeGrant.objects.filter(
        institution__isnull=True,
        academic_cycle__isnull=True,
        grade__isnull=True,
        section__isnull=True,
        subject__isnull=True,
        teaching_assignment__isnull=True,
        student__isnull=True,
        module_key="",
        is_active=True,
    ).update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [("identity", "0005_seed_attendance_jornada_configure_permission")]

    operations = [
        migrations.RunPython(deactivate_empty_scope_grants, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="scopegrant",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(is_active=False)
                    | models.Q(institution__isnull=False)
                    | models.Q(academic_cycle__isnull=False)
                    | models.Q(grade__isnull=False)
                    | models.Q(section__isnull=False)
                    | models.Q(subject__isnull=False)
                    | models.Q(teaching_assignment__isnull=False)
                    | models.Q(student__isnull=False)
                    | ~models.Q(module_key="")
                ),
                name="identity_scope_grant_has_dimension",
            ),
        )
    ]
