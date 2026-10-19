"""
ADR-0011: permisos atomicos nuevos.

- ``account_update``: editar usuario y correo de otra cuenta (U7).
- ``person_view``, ``person_edit``, ``document_type_manage``: existen para que
  el dueño de Personas y Tipos de documento los exija en el backend. Hasta
  entonces el menu los usa solo como presentacion (ADR-0011, provisional).
"""

from django.db import migrations

PERMISSIONS = (
    ("account_update", "Editar cuentas"),
    ("person_view", "Ver personas"),
    ("person_edit", "Editar personas"),
    ("document_type_manage", "Administrar tipos de documento"),
)


def seed_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    content_type, _ = ContentType.objects.get_or_create(app_label="identity", model="role")
    for codename, name in PERMISSIONS:
        Permission.objects.update_or_create(
            content_type=content_type, codename=codename, defaults={"name": name}
        )


class Migration(migrations.Migration):
    dependencies = [("identity", "0014_account_public_id_spanish_labels_cycle_revert")]

    operations = [migrations.RunPython(seed_permissions, migrations.RunPython.noop)]
