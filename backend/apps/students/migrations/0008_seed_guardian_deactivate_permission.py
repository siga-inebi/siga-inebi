"""#632 G3: explicitly approved permission; no automatic grants to existing roles."""

from django.db import migrations


def seed_permission(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    database = schema_editor.connection.alias
    content_type, _ = ContentType.objects.using(database).get_or_create(
        app_label="identity", model="role"
    )
    Permission.objects.using(database).update_or_create(
        content_type=content_type,
        codename="guardian_deactivate",
        defaults={"name": "Desactivar encargados"},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0017_grant_account_update_to_account_creators"),
        ("students", "0007_add_transferred_student_status"),
    ]
    operations = [migrations.RunPython(seed_permission, migrations.RunPython.noop)]
