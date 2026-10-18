import { useContext } from "react";

import { AuthContext } from "@auth/context.js";
import { hasAnyPermission } from "@auth/permissions.js";

/**
 * Permisos efectivos de la sesion para decidir que se muestra (ux-ui 1.4).
 *
 * `can(codes)` es verdadero si la cuenta tiene AL MENOS UNO de los permisos.
 */
export function usePermissions() {
  // Sin proveedor (componentes probados en aislamiento) no hay sesion: se
  // deniega por defecto en vez de fallar.
  const user = useContext(AuthContext)?.user ?? null;
  return {
    user,
    can: (codes) =>
      hasAnyPermission(user, Array.isArray(codes) ? codes : [codes]),
  };
}
