"""
ADR-0011, decision de identidad 5: editar cuentas paso de `account.create` a un
permiso propio, `account.update`.

Para que ningun rol pierda la edicion de cuentas al desplegar, todo rol que hoy
tiene `account_create` recibe tambien `account_update`. Hecho visible: los roles
con `account.create` reciben `account.update` al migrar; administracion debe
revisarlos y retirar el permiso donde no corresponda. Una migracion no tiene
actor de peticion, asi que no deja asiento de bitacora; este docstring, ADR-0011
y docs/architecture/api-conventions.md son el registro.

- Idempotente: `role.permissions.add` no duplica filas de la tabla intermedia.
- Reversa sin efecto, a proposito: quitar `account_update` al revertir podria
  borrar concesiones que un administrador hizo a mano despues de migrar, y eso
  es una perdida de autorizacion que nadie pidio.
"""

from django.db import migrations


def grant_account_update_to_account_creators(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    Role = apps.get_model("identity", "Role")
    try:
        account_update = Permission.objects.get(
            content_type__app_label="identity",
            content_type__model="role",
            codename="account_update",
        )
    except Permission.DoesNotExist:
        return
    for role in Role.objects.filter(permissions__codename="account_create").distinct():
        role.permissions.add(account_update)


class Migration(migrations.Migration):
    dependencies = [("identity", "0016_user_session")]

    operations = [
        migrations.RunPython(grant_account_update_to_account_creators, migrations.RunPython.noop)
    ]
