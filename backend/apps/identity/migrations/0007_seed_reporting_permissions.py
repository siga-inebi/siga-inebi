from django.db import migrations

PERMISSIONS = (
    ("reporting_alert_view", "Can view reporting alerts"),
    ("reporting_alert_acknowledge", "Can acknowledge reporting alerts"),
    ("reporting_alert_evaluate", "Can trigger reporting alert evaluation"),
    ("reporting_absence_threshold_configure", "Can configure the absence threshold"),
)


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
        ("identity", "0006_scope_grant_requires_dimension"),
    ]

    operations = [migrations.RunPython(seed_permissions, migrations.RunPython.noop)]
