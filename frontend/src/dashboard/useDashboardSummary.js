import { useModuleCountsState } from "@app/useModuleCounts.js";
import { apiClient } from "@shared/api/apiClient.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";

/**
 * Datos agregados del panel: conteos por dominio y salud del servicio.
 *
 * Los conteos NO descargan padrones (docs/ux-ui.md 1.7). Antes este hook
 * recorria todos los estudiantes, docentes y encargados para hacer
 * `records.length`, con el tope de 1 000 de por medio. Ahora reutiliza
 * `useModuleCounts`, la misma fuente (y la misma cache) que los badges del
 * menu lateral: una peticion de una fila por modulo, usando `count`.
 *
 * Un conteo que falla o que la cuenta no puede ver queda en `null` sin tumbar
 * los demas.
 *
 * @param {object} user Usuario de sesion.
 */
export function useDashboardSummary(user) {
  const { counts: moduleCounts, loading } = useModuleCountsState(
    Boolean(user),
    user
  );
  const health = useResourceQuery(queryKeys.dashboard.health(), () =>
    apiClient.get("/health/")
  );

  const counts = {
    students: moduleCounts.alumnos,
    teachers: moduleCounts.docentes,
    guardians: moduleCounts.padres,
  };

  return {
    counts,
    health: { data: health.data, error: health.error },
    loading,
  };
}
