from django.db import migrations


PERMISSIONS = (
    ("auth_login", "Can log in"),
    ("auth_logout", "Can log out"),
    ("account_create", "Can create accounts"),
    ("account_activate", "Can issue account activation challenges"),
    ("account_disable", "Can disable accounts"),
    ("role_assign", "Can assign roles"),
    ("scope_assign", "Can assign scopes"),
    ("student_view_basic", "Can view student basic data"),
    ("student_view_sensitive", "Can view sensitive student data"),
    ("student_edit_basic", "Can edit student basic data"),
    ("enrollment_create", "Can create enrollments"),
    ("enrollment_update", "Can update enrollments"),
    ("attendance_scan", "Can scan attendance credentials"),
    ("attendance_record_entry", "Can record attendance entries"),
    ("attendance_record_exit", "Can record attendance exits"),
    ("attendance_declared_close", "Can perform declared attendance close"),
    ("attendance_record_manual", "Can record attendance manually"),
    ("attendance_justification_request", "Can request attendance justifications"),
    ("attendance_justification_resolve", "Can resolve attendance justifications"),
    ("grade_write", "Can write grades"),
    ("grade_correct", "Can correct grades"),
    ("document_upload", "Can upload documents"),
    ("document_read", "Can read documents"),
    ("document_download", "Can download documents"),
    ("document_issue", "Can issue documents"),
    ("audit_read", "Can read audit events"),
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
        ("identity", "0003_activationchallenge"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(seed_permissions, migrations.RunPython.noop)]
