import { hasAnyPermission } from "@auth/permissions.js";
import { useAuth } from "@auth/useAuth.js";

/**
 * Permisos efectivos de la sesion para decidir que se muestra (ux-ui 1.4).
 *
 * `can(codes)` es verdadero si la cuenta tiene AL MENOS UNO de los permisos.
 */
export function usePermissions() {
  const { user } = useAuth();
  return {
    user,
    can: (codes) =>
      hasAnyPermission(user, Array.isArray(codes) ? codes : [codes]),
  };
}
