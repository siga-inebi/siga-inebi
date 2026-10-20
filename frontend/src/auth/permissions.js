/**
 * permissions.js — Presentacion por permisos efectivos (docs/ux-ui.md 1.4).
 *
 * `/auth/me/` devuelve los permisos atomicos efectivos de la cuenta
 * (`user.permissions`, codigos con punto). Con ellos el menu, las rutas y los
 * botones se ocultan o deshabilitan en vez de dejar que la persona se entere
 * con un 403 despues de hacer clic.
 *
 * Esto es SOLO presentacion. El backend sigue siendo la autoridad: cada
 * operacion vuelve a autorizarse alla con permiso y alcance, y deniega por
 * defecto. Aqui tampoco se replica ninguna regla de negocio: solo se pregunta
 * "¿tiene la cuenta este permiso?".
 */

/** Codigos de permiso que la interfaz consulta. Deben existir en el catalogo atomico. */
export const PERMISSION = Object.freeze({
  ACCOUNT_CREATE: "account.create",
  ACCOUNT_ACTIVATE: "account.activate",
  ACCOUNT_UPDATE: "account.update",
  PERSON_VIEW: "person.view",
  PERSON_EDIT: "person.edit",
  DOCUMENT_TYPE_MANAGE: "document_type.manage",
  ACCOUNT_DISABLE: "account.disable",
  ROLE_ASSIGN: "role.assign",
  SCOPE_ASSIGN: "scope.assign",
  ACADEMIC_CYCLE_REOPEN: "academic_cycle.reopen",
  ACADEMIC_CYCLE_REVERT: "academic_cycle.revert",
  STUDENT_VIEW_BASIC: "student.view_basic",
  STUDENT_EDIT_BASIC: "student.edit_basic",
  ENROLLMENT_CREATE: "enrollment.create",
  ENROLLMENT_UPDATE: "enrollment.update",
  ATTENDANCE_SCAN: "attendance.scan",
  ATTENDANCE_RECORD_ENTRY: "attendance.record_entry",
  ATTENDANCE_RECORD_EXIT: "attendance.record_exit",
  ATTENDANCE_RECORD_MANUAL: "attendance.record_manual",
  ATTENDANCE_DECLARED_CLOSE: "attendance.declared_close",
  ATTENDANCE_JORNADA_CONFIGURE: "attendance.jornada.configure",
  ATTENDANCE_CREDENTIAL_ISSUE: "attendance.credential.issue",
  ATTENDANCE_JUSTIFICATION_REQUEST: "attendance.justification.request",
  ATTENDANCE_JUSTIFICATION_RESOLVE: "attendance.justification.resolve",
  ATTENDANCE_PERMIT_REQUEST: "attendance.permit.request",
  ATTENDANCE_PERMIT_RESOLVE: "attendance.permit.resolve",
  EVALUATION_CONFIGURE_UNITS: "evaluation.configure_units",
  GRADE_WRITE: "grade.write",
  GRADE_CORRECT: "grade.correct",
  DOCUMENT_UPLOAD: "document.upload",
  DOCUMENT_ISSUE: "document.issue",
  REPORTING_ALERT_VIEW: "reporting.alert.view",
  AUDIT_READ: "audit.read",
  RETENTION_POLICY_DECLARE: "retention_policy.declare",
  PLATFORM_MONITOR: "platform.monitor",
});

/** Cualquiera de estos habilita la administracion de cuentas. */
export const ACCOUNT_ADMIN_PERMISSIONS = [
  PERMISSION.ACCOUNT_CREATE,
  PERMISSION.ACCOUNT_UPDATE,
  PERMISSION.ACCOUNT_ACTIVATE,
  PERMISSION.ACCOUNT_DISABLE,
];

/**
 * Permisos de cada modulo del menu: basta con UNO. Un modulo sin entrada aqui
 * no tiene un permiso atomico que lo controle en el backend (sus lecturas solo
 * exigen sesion), asi que se muestra a toda cuenta autenticada.
 */
export const MODULE_PERMISSIONS = Object.freeze({
  alumnos: [PERMISSION.STUDENT_VIEW_BASIC],
  matriculas: [
    PERMISSION.ENROLLMENT_CREATE,
    PERMISSION.ENROLLMENT_UPDATE,
    PERMISSION.STUDENT_VIEW_BASIC,
  ],
  asistencia: [
    PERMISSION.ATTENDANCE_SCAN,
    PERMISSION.ATTENDANCE_RECORD_ENTRY,
    PERMISSION.ATTENDANCE_RECORD_EXIT,
    PERMISSION.ATTENDANCE_RECORD_MANUAL,
    PERMISSION.ATTENDANCE_DECLARED_CLOSE,
    PERMISSION.ATTENDANCE_JORNADA_CONFIGURE,
    PERMISSION.ATTENDANCE_CREDENTIAL_ISSUE,
    PERMISSION.ATTENDANCE_JUSTIFICATION_REQUEST,
    PERMISSION.ATTENDANCE_JUSTIFICATION_RESOLVE,
    PERMISSION.ATTENDANCE_PERMIT_REQUEST,
    PERMISSION.ATTENDANCE_PERMIT_RESOLVE,
    PERMISSION.STUDENT_VIEW_BASIC,
  ],
  evaluacion: [
    PERMISSION.EVALUATION_CONFIGURE_UNITS,
    PERMISSION.GRADE_WRITE,
    PERMISSION.GRADE_CORRECT,
    PERMISSION.STUDENT_VIEW_BASIC,
  ],
  alertas: [PERMISSION.REPORTING_ALERT_VIEW],
  // Administracion (2.17.6): solo quien tiene esos permisos ve el grupo.
  cuentas: ACCOUNT_ADMIN_PERMISSIONS,
  roles: [PERMISSION.ROLE_ASSIGN],
  // PROVISIONAL (ADR-0011): solo presentacion hasta que el dueño de Personas y
  // Tipos de documento exija estos permisos en el backend.
  personas: [PERMISSION.PERSON_VIEW, PERMISSION.PERSON_EDIT],
  "tipos-documento": [PERMISSION.DOCUMENT_TYPE_MANAGE],
  auditoria: [PERMISSION.AUDIT_READ, PERMISSION.RETENTION_POLICY_DECLARE],
  plataforma: [PERMISSION.PLATFORM_MONITOR],
});

function permissionSet(user) {
  return new Set(user?.permissions ?? []);
}

/** ¿Tiene la cuenta este permiso efectivo? Sin sesion, nunca. */
export function hasPermission(user, code) {
  if (!user) return false;
  if (user.is_superuser) return true;
  return permissionSet(user).has(code);
}

/** ¿Tiene al menos uno? Una lista vacia no exige nada. */
export function hasAnyPermission(user, codes = []) {
  if (!user) return false;
  if (!codes || codes.length === 0) return true;
  if (user.is_superuser) return true;
  const granted = permissionSet(user);
  return codes.some((code) => granted.has(code));
}

/** ¿Puede ver este modulo del registro de navegacion? */
export function canAccessModule(user, item) {
  return hasAnyPermission(user, item?.permissions);
}

// Compatibilidad: firmas que ya consumian `navigation.js` y otras pantallas.
export function canViewAlumnos(user) {
  return hasAnyPermission(user, MODULE_PERMISSIONS.alumnos);
}

export function canViewDocentes(user) {
  return Boolean(user);
}

export function canViewPadres(user) {
  return Boolean(user);
}

export function canViewSedes(user) {
  return Boolean(user);
}

export function canViewNiveles(user) {
  return Boolean(user);
}

export function canViewCursos(user) {
  return Boolean(user);
}
