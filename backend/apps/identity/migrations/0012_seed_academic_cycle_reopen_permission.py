from django.db import migrations

PERMISSIONS = (("academic_cycle_reopen", "Can reopen a closed academic cycle"),)


def seed_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    content_type, _ = ContentType.objects.get_or_create(app_label="identity", model="role")
    for codename, name in PERMISSIONS:
        Permission.objects.update_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0011_password_reset_challenge"),
    ]

    operations = [migrations.RunPython(seed_permissions, migrations.RunPython.noop)]
