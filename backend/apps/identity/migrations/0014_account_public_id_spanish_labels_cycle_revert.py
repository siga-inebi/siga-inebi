"""
ADR-0011 / docs/ux-ui.md 2.17:

- ``UserAccount.public_id``: identificador opaco para la API. Se agrega nulo,
  se rellena fila por fila (un ``default`` en ``AddField`` repetiria el mismo
  UUID en todas las filas existentes y romperia el indice unico) y despues se
  vuelve obligatorio y unico.
- Etiquetas de estado de la cuenta en espanol (U8).
- Permiso nuevo ``academic_cycle_revert`` (D6) y nombres en espanol de todo el
  catalogo atomico (RO2). Los codigos no cambian: solo el texto visible.
"""

import uuid

from django.db import migrations, models

SPANISH_PERMISSION_NAMES = {
    "auth_login": "Iniciar sesión",
    "auth_logout": "Cerrar sesión",
    "account_create": "Crear cuentas",
    "account_activate": "Activar, reactivar y desbloquear cuentas",
    "account_disable": "Desactivar cuentas y restablecer acceso",
    "role_assign": "Administrar roles y asignaciones",
    "scope_assign": "Administrar catálogos institucionales",
    "student_view_basic": "Ver datos básicos del estudiante",
    "student_view_sensitive": "Ver datos sensibles del estudiante",
    "student_edit_basic": "Editar datos básicos del estudiante",
    "enrollment_create": "Matricular",
    "enrollment_update": "Modificar matrículas",
    "attendance_scan": "Escanear credenciales",
    "attendance_credential_issue": "Emitir credenciales",
    "attendance_credential_resolve": "Resolver credenciales",
    "attendance_record_entry": "Registrar ingresos",
    "attendance_record_exit": "Registrar egresos",
    "attendance_declared_close": "Cerrar asistencia de sección",
    "attendance_record_manual": "Registrar asistencia manual",
    "attendance_justification_request": "Solicitar justificaciones",
    "attendance_justification_resolve": "Resolver justificaciones",
    "attendance_permit_request": "Solicitar permisos de salida",
    "attendance_permit_resolve": "Resolver permisos de salida",
    "attendance_jornada_configure": "Configurar la jornada",
    "evaluation_configure_units": "Configurar evaluación",
    "grade_write": "Registrar notas",
    "grade_correct": "Corregir notas",
    "academic_cycle_reopen": "Reabrir ciclo escolar",
    "academic_cycle_revert": "Volver un ciclo a borrador",
    "document_upload": "Subir documentos",
    "document_read": "Consultar documentos",
    "document_download": "Descargar documentos",
    "document_issue": "Emitir documentos oficiales",
    "reporting_alert_view": "Ver alertas",
    "reporting_alert_acknowledge": "Atender alertas",
    "reporting_alert_evaluate": "Evaluar alertas",
    "reporting_absence_threshold_configure": "Configurar umbral de inasistencia",
    "audit_read": "Consultar la bitácora",
    "retention_policy_declare": "Declarar plazos de retención",
    "platform_monitor": "Monitorear la plataforma",
}

# Permisos que esta migracion crea si no existen. El resto solo se renombra:
# crear aqui un permiso que otra migracion siembra duplicaria esa responsabilidad.
NEW_PERMISSIONS = ("academic_cycle_revert",)


def fill_account_public_ids(apps, schema_editor):
    UserAccount = apps.get_model("identity", "UserAccount")
    for account in UserAccount.objects.filter(public_id__isnull=True).only("pk"):
        UserAccount.objects.filter(pk=account.pk).update(public_id=uuid.uuid4())


def sync_permission_catalogue(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    content_type, _ = ContentType.objects.get_or_create(app_label="identity", model="role")
    for codename in NEW_PERMISSIONS:
        Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": SPANISH_PERMISSION_NAMES[codename]},
        )
    for codename, name in SPANISH_PERMISSION_NAMES.items():
        Permission.objects.filter(content_type=content_type, codename=codename).update(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("identity", "0013_seed_platform_monitor_permission"),
    ]

    operations = [
        migrations.AddField(
            model_name="useraccount",
            name="public_id",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(fill_account_public_ids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="useraccount",
            name="public_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name="useraccount",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pendiente"),
                    ("active", "Activa"),
                    ("blocked", "Bloqueada"),
                    ("disabled", "Desactivada"),
                ],
                default="active",
                max_length=20,
            ),
        ),
        migrations.RunPython(sync_permission_catalogue, migrations.RunPython.noop),
    ]
