export const anonymousSession = { authenticated: false, user: null };

/**
 * Permisos efectivos de una cuenta con acceso a todo el catalogo. Las pruebas
 * de navegacion la usan para ver todos los modulos; las de permisos arman su
 * propia lista (ver `permissionsTests`).
 */
export const ALL_PERMISSIONS = [
  "auth.login",
  "auth.logout",
  "account.create",
  "account.activate",
  "account.disable",
  "role.assign",
  "scope.assign",
  "student.view_basic",
  "student.view_sensitive",
  "student.edit_basic",
  "enrollment.create",
  "enrollment.update",
  "attendance.scan",
  "attendance.record_entry",
  "attendance.record_exit",
  "attendance.declared_close",
  "attendance.record_manual",
  "attendance.jornada.configure",
  "evaluation.configure_units",
  "grade.write",
  "grade.correct",
  "document.upload",
  "document.read",
  "document.download",
  "document.issue",
  "reporting.alert.view",
  "audit.read",
  "retention_policy.declare",
  "platform.monitor",
];

export const authenticatedSession = {
  authenticated: true,
  user: {
    public_id: "00000000-0000-4000-8000-000000000001",
    username: "admin",
    email: "admin@example.test",
    status: "active",
    status_display: "Activa",
    is_superuser: false,
    permissions: ALL_PERMISSIONS,
    roles: [],
    session_idle_timeout_minutes: 30,
    person: {
      public_id: "00000000-0000-4000-8000-000000000002",
      first_name: "Demo",
      last_name: "Admin",
    },
  },
};
