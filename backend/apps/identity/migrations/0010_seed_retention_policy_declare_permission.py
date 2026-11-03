from django.db import migrations

PERMISSIONS = (("retention_policy_declare", "Can declare data retention periods"),)


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
        ("identity", "0009_role_session_timeout_and_account_person_required"),
    ]

    operations = [migrations.RunPython(seed_permissions, migrations.RunPython.noop)]
