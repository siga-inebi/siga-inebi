/**
 * Etiquetas visibles de identidad y acceso (docs/ux-ui.md MC3, U8).
 *
 * El backend ya devuelve `status_display` en espanol; estas tablas cubren lo
 * que se pinta sin pasar por el (filtros, chips, acciones de la bitacora) y
 * sirven de respaldo si un cliente viejo no envia la etiqueta.
 */

export const ACCOUNT_STATUS_LABEL = {
  pending: "Pendiente",
  active: "Activa",
  blocked: "Bloqueada",
  disabled: "Desactivada",
};

export const ACCOUNT_STATUS_VARIANT = {
  active: "success",
  pending: "warning",
  disabled: "neutral",
  blocked: "danger",
};

export const ACCOUNT_STATUS_OPTIONS = Object.entries(ACCOUNT_STATUS_LABEL).map(
  ([value, label]) => ({ value, label })
);

export function accountStatusLabel(account) {
  if (!account) return "";
  return (
    account.status_display ??
    ACCOUNT_STATUS_LABEL[account.status] ??
    account.status
  );
}

export const ASSIGNMENT_STATUS_LABEL = {
  active: "Vigente",
  expiring: "Por vencer",
  scheduled: "Programada",
  ended: "Finalizada",
};

export const ASSIGNMENT_STATUS_VARIANT = {
  active: "success",
  expiring: "warning",
  scheduled: "primary",
  ended: "neutral",
};

/** Acciones de bitacora que se muestran en el historial de una cuenta. */
export const AUDIT_ACTION_LABEL = {
  "identity.login.succeeded": "Inicio de sesión",
  "identity.login.denied": "Intento de inicio de sesión rechazado",
  "identity.login.lockout_cleared": "Bloqueo levantado al iniciar sesión",
  "identity.session.expired": "Sesión vencida por inactividad",
  "identity.session.closed_current": "Cierre de sesión",
  "identity.session.closed_all": "Cierre de todas las sesiones",
  "identity.session.closed_administratively":
    "Sesiones cerradas por administración",
  "identity.account.created": "Cuenta creada",
  "identity.account.activated": "Cuenta activada",
  "identity.account.updated": "Cuenta editada",
  "identity.account.disabled": "Cuenta desactivada",
  "identity.account.reactivated": "Cuenta reactivada",
  "identity.account.unlocked": "Cuenta desbloqueada",
  "identity.activation_challenge.issued": "Código de activación emitido",
  "identity.activation_challenge.denied": "Activación rechazada",
  "identity.password.changed": "Contraseña cambiada",
  "identity.password_reset.issued": "Enlace de restablecimiento emitido",
  "identity.password_reset.consumed": "Contraseña restablecida",
};

export function auditActionLabel(action) {
  return AUDIT_ACTION_LABEL[action] ?? action;
}

/** Perfiles de una persona candidata a cuenta. */
export const PROFILE_LABEL = {
  teacher: "Docente",
  student: "Estudiante",
  guardian: "Encargado",
};
