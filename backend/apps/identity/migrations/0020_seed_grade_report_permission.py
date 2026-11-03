"""Informe de calificaciones en PDF: permiso aprobado, sin concesiones automaticas."""

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
        codename="grade_report",
        defaults={"name": "Imprimir notas"},
    )


class Migration(migrations.Migration):
    dependencies = [("identity", "0019_seed_credential_print_permission")]
    operations = [migrations.RunPython(seed_permission, migrations.RunPython.noop)]
