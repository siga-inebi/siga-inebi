import { usePermissions } from "@auth/usePermissions.js";

/**
 * Muestra `children` solo si la cuenta tiene alguno de los permisos; si no,
 * `fallback` (por defecto nada). Es presentacion: el backend vuelve a autorizar.
 *
 * @param {object} props
 * @param {string|string[]} props.permission
 * @param {React.ReactNode} [props.fallback]
 */
export function Can({ children, fallback = null, permission }) {
  const { can } = usePermissions();
  return can(permission) ? children : fallback;
}
