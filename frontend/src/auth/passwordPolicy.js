import { authService } from "@auth/authService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";

/**
 * Reglas REALES de contraseña (docs/ux-ui.md MC2).
 *
 * Antes la ventana decia "al menos 8 caracteres" mientras el backend aplicaba
 * todos los validadores de Django (contraseña comun, solo numeros, parecida al
 * usuario). Ahora la lista sale del backend (`/identity/password-policy/`), que
 * la lee de los mismos validadores que aplica: no hay dos fuentes que puedan
 * contradecirse.
 */
export function usePasswordRules() {
  const { data, loading, error } = useResourceQuery(
    queryKeys.identity.passwordPolicy(),
    () => authService.passwordPolicy(),
    { staleTime: Infinity }
  );
  return { rules: data?.rules ?? [], loading, error };
}

/** Mensajes del backend para un campo (`{error: {detail: {campo: [...]}}}`). */
export function fieldErrors(error, field) {
  const detail = error?.payload?.error?.detail;
  if (!detail || typeof detail !== "object") return [];
  const value = detail[field];
  if (Array.isArray(value)) return value.map(String);
  return value ? [String(value)] : [];
}
