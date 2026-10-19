"""
Catalogo cerrado de permisos atomicos (RF-PER-001).

Cada permiso tiene un codigo publico con punto (``student.view_basic``), que es
lo que viaja por la API, y un ``codename`` de Django con guion bajo, que es lo
que se guarda. Ademas de la etiqueta, cada permiso declara una descripcion de
una linea y el grupo funcional al que pertenece: la pantalla de roles los
agrupa por modulo (docs/ux-ui.md, RO1 y RO2) y nadie deberia tener que adivinar
que cubre "Ver datos basicos del estudiante".

Las etiquetas viven aqui y no en la base: el nombre guardado en
``auth.Permission`` se sincroniza por migracion, pero la fuente de verdad es
este modulo.
"""

#: Grupos funcionales, en el orden en que se muestran.
PERMISSION_GROUPS = (
    ("accounts", "Cuentas y accesos"),
    ("people", "Personas"),
    ("students", "Estudiantes"),
    ("teachers", "Docentes"),
    ("enrolment", "Matrícula"),
    ("attendance", "Asistencia"),
    ("evaluation", "Evaluación"),
    ("cycle", "Ciclo escolar"),
    ("documents", "Documentos"),
    ("alerts", "Alertas"),
    ("audit", "Auditoría"),
    ("platform", "Plataforma"),
)

PERMISSION_GROUP_LABELS = dict(PERMISSION_GROUPS)

#: (codigo publico, etiqueta, descripcion, grupo)
PERMISSION_CATALOGUE = (
    (
        "teacher.deactivate",
        "Desactivar docentes",
        "Permite desactivar el perfil docente conservando su historial, con alcance teachers.",
        "teachers",
    ),
    (
        "guardian.deactivate",
        "Desactivar encargados",
        "Permite desactivar el perfil de encargado conservando sus vinculos, con alcance students.",
        "students",
    ),
    ("auth.login", "Iniciar sesión", "Permite entrar al sistema con su cuenta.", "accounts"),
    ("auth.logout", "Cerrar sesión", "Permite cerrar su propia sesión.", "accounts"),
    (
        "account.create",
        "Crear cuentas",
        "Permite dar acceso al sistema a una persona registrada.",
        "accounts",
    ),
    (
        "account.update",
        "Editar cuentas",
        "Permite corregir el usuario y el correo de otra cuenta. La propia se edita en Mi cuenta.",
        "accounts",
    ),
    (
        "account.activate",
        "Activar, reactivar y desbloquear cuentas",
        "Permite reemitir códigos de activación, reactivar cuentas desactivadas y "
        "levantar bloqueos temporales.",
        "accounts",
    ),
    (
        "account.disable",
        "Desactivar cuentas y restablecer acceso",
        "Permite listar cuentas, desactivarlas, cerrar sus sesiones y emitir enlaces de "
        "restablecimiento de contraseña.",
        "accounts",
    ),
    (
        "role.assign",
        "Administrar roles y asignaciones",
        "Permite crear y editar roles y asignarlos o revocarlos a otras cuentas.",
        "accounts",
    ),
    (
        "scope.assign",
        "Administrar catálogos institucionales",
        "Permite modificar sedes, niveles, cursos, ciclos y asignaciones docentes dentro del "
        "alcance asignado.",
        "accounts",
    ),
    (
        "person.view",
        "Ver personas",
        "Permite consultar el registro base de personas de la institución.",
        "people",
    ),
    (
        "person.edit",
        "Editar personas",
        "Permite registrar, corregir y desactivar personas del registro base.",
        "people",
    ),
    (
        "student.view_basic",
        "Ver datos básicos del estudiante",
        "Permite ver nombre, código, foto y matrícula; no incluye salud ni observaciones.",
        "students",
    ),
    (
        "student.view_sensitive",
        "Ver datos sensibles del estudiante",
        "Permite ver salud, observaciones y contactos de familia del estudiante.",
        "students",
    ),
    (
        "student.edit_basic",
        "Editar datos básicos del estudiante",
        "Permite registrar estudiantes y corregir sus datos de identificación.",
        "students",
    ),
    (
        "enrollment.create",
        "Matricular",
        "Permite registrar matrículas y reinscripciones.",
        "enrolment",
    ),
    (
        "enrollment.update",
        "Modificar matrículas",
        "Permite registrar movimientos de matrícula: cambios de sección, retiros y traslados.",
        "enrolment",
    ),
    (
        "attendance.scan",
        "Escanear credenciales",
        "Permite registrar asistencia escaneando el carné del estudiante.",
        "attendance",
    ),
    (
        "attendance.credential.issue",
        "Emitir credenciales",
        "Permite emitir, imprimir y revocar el carné QR del estudiante.",
        "attendance",
    ),
    (
        "attendance.credential.resolve",
        "Resolver credenciales",
        "Permite identificar al estudiante a partir del código de su carné.",
        "attendance",
    ),
    (
        "attendance.record_entry",
        "Registrar ingresos",
        "Permite registrar la entrada del estudiante.",
        "attendance",
    ),
    (
        "attendance.record_exit",
        "Registrar egresos",
        "Permite registrar la salida del estudiante.",
        "attendance",
    ),
    (
        "attendance.declared_close",
        "Cerrar asistencia de sección",
        "Permite declarar el cierre de la asistencia de una sección.",
        "attendance",
    ),
    (
        "attendance.record_manual",
        "Registrar asistencia manual",
        "Permite registrar asistencia sin escaneo, con motivo.",
        "attendance",
    ),
    (
        "attendance.justification.request",
        "Solicitar justificaciones",
        "Permite enviar justificaciones de inasistencia.",
        "attendance",
    ),
    (
        "attendance.justification.resolve",
        "Resolver justificaciones",
        "Permite aprobar o rechazar justificaciones de inasistencia.",
        "attendance",
    ),
    (
        "attendance.permit.request",
        "Solicitar permisos de salida",
        "Permite solicitar permisos de salida anticipada o ingreso tardío.",
        "attendance",
    ),
    (
        "attendance.permit.resolve",
        "Resolver permisos de salida",
        "Permite aprobar o rechazar permisos de salida.",
        "attendance",
    ),
    (
        "attendance.jornada.configure",
        "Configurar la jornada",
        "Permite cambiar los parámetros de la jornada: horarios límite y ventana de escaneo.",
        "attendance",
    ),
    (
        "evaluation.configure_units",
        "Configurar evaluación",
        "Permite configurar y cerrar unidades de evaluación y ventanas de captura.",
        "evaluation",
    ),
    ("grade.write", "Registrar notas", "Permite registrar calificaciones.", "evaluation"),
    (
        "grade.correct",
        "Corregir notas",
        "Permite corregir calificaciones ya registradas, con motivo.",
        "evaluation",
    ),
    (
        "academic_cycle.reopen",
        "Reabrir ciclo escolar",
        "Permite reabrir un ciclo cerrado, con motivo (RF-CIC-005).",
        "cycle",
    ),
    (
        "academic_cycle.revert",
        "Volver un ciclo a borrador",
        "Permite devolver a borrador un ciclo activado por error, antes de que tenga "
        "actividad (ADR-0011, D3 y D6).",
        "cycle",
    ),
    (
        "document.upload",
        "Subir documentos",
        "Permite adjuntar documentos al expediente.",
        "documents",
    ),
    (
        "document.read",
        "Consultar documentos",
        "Permite ver el expediente documental.",
        "documents",
    ),
    (
        "document.download",
        "Descargar documentos",
        "Permite descargar documentos del expediente.",
        "documents",
    ),
    (
        "document.issue",
        "Emitir documentos oficiales",
        "Permite emitir constancias, certificados y reportes oficiales.",
        "documents",
    ),
    (
        "document_type.manage",
        "Administrar tipos de documento",
        "Permite crear, editar y desactivar tipos de documento.",
        "documents",
    ),
    (
        "reporting.alert.view",
        "Ver alertas",
        "Permite consultar las alertas de asistencia.",
        "alerts",
    ),
    (
        "reporting.alert.acknowledge",
        "Atender alertas",
        "Permite marcar alertas como atendidas.",
        "alerts",
    ),
    (
        "reporting.alert.evaluate",
        "Evaluar alertas",
        "Permite ejecutar la evaluación de alertas.",
        "alerts",
    ),
    (
        "reporting.absence_threshold.configure",
        "Configurar umbral de inasistencia",
        "Permite cambiar el umbral que dispara las alertas de inasistencia.",
        "alerts",
    ),
    (
        "audit.read",
        "Consultar la bitácora",
        "Permite consultar y exportar la bitácora de auditoría.",
        "audit",
    ),
    (
        "retention_policy.declare",
        "Declarar plazos de retención",
        "Permite declarar el plazo de retención de una categoría de datos (RNF-LEG-001).",
        "audit",
    ),
    (
        "platform.monitor",
        "Monitorear la plataforma",
        "Permite consultar tareas programadas, su salud y el estado de los respaldos.",
        "platform",
    ),
)

#: Compatibilidad: pares (codigo, etiqueta) que consumen el sembrado y la API.
ATOMIC_PERMISSIONS = tuple((code, label) for code, label, _desc, _group in PERMISSION_CATALOGUE)

PERMISSION_DETAILS = {
    code: {"label": label, "description": description, "group": group}
    for code, label, description, group in PERMISSION_CATALOGUE
}


def permission_codename(code):
    return code.replace(".", "_")


ATOMIC_PERMISSION_CODENAMES = tuple(permission_codename(code) for code, _name in ATOMIC_PERMISSIONS)
ATOMIC_PERMISSION_CODES_BY_CODENAME = {
    permission_codename(code): code for code, _name in ATOMIC_PERMISSIONS
}
