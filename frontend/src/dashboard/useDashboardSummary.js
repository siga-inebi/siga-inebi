import { useModuleCountsState } from "@app/useModuleCounts.js";
import { hasAnyPermission, MODULE_PERMISSIONS } from "@auth/permissions.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";

/**
 * Datos agregados del panel operativo.
 *
 * Los conteos NO descargan padrones (docs/ux-ui.md 1.7). Antes este hook
 * recorria todos los estudiantes, docentes y encargados para hacer
 * `records.length`, con el tope de 1 000 de por medio. Ahora reutiliza
 * `useModuleCounts`, la misma fuente (y la misma cache) que los badges del
 * menu lateral: una peticion de una fila por modulo, usando `count`.
 *
 * Cada fuente conserva la autorizacion de su dominio. El panel no crea reglas
 * nuevas: compone ciclos, matriculas y alertas que la cuenta ya puede consultar.
 * Una fuente que falla o que la cuenta no puede ver queda en `null` sin tumbar
 * las demas.
 *
 * @param {object} user Usuario de sesion.
 */
export function useDashboardSummary(user) {
  const { counts: moduleCounts, loading } = useModuleCountsState(
    Boolean(user),
    user
  );
  const cyclesQuery = useResourceQuery(
    queryKeys.dashboard.cycles(),
    () =>
      import("@cycles/cyclesService.js").then((module) =>
        module.cyclesService.list({ page_size: 100 })
      ),
    { enabled: Boolean(user) }
  );

  const cycles = cyclesQuery.data?.results ?? [];
  const activeCycle = cycles.find((cycle) => cycle.status === "active") ?? null;
  const draftCycle =
    cycles
      .filter((cycle) => cycle.status === "draft")
      .sort((left, right) => right.year - left.year)[0] ?? null;

  const canViewEnrolments = hasAnyPermission(
    user,
    MODULE_PERMISSIONS.matriculas
  );
  const enrolmentsQuery = useResourceQuery(
    queryKeys.dashboard.activeEnrolments(activeCycle?.public_id),
    () =>
      import("@enrolments/enrolmentsService.js").then((module) =>
        module.enrolmentsService.listActive({
          academic_cycle_id: activeCycle.public_id,
          page_size: 1,
        })
      ),
    { enabled: Boolean(activeCycle && canViewEnrolments) }
  );

  const canViewAlerts = hasAnyPermission(user, MODULE_PERMISSIONS.alertas);
  const alertsQuery = useResourceQuery(
    queryKeys.dashboard.pendingAlerts(),
    () =>
      import("@reporting/reportingService.js").then((module) =>
        module.reportingService.listAlerts({
          acknowledged: false,
          is_active: true,
          page_size: 3,
        })
      ),
    { enabled: Boolean(user && canViewAlerts) }
  );

  const counts = {
    students: moduleCounts.alumnos,
    teachers: moduleCounts.docentes,
    guardians: moduleCounts.padres,
  };

  return {
    counts,
    activeCycle,
    draftCycle,
    activeEnrolments: canViewEnrolments
      ? (enrolmentsQuery.data?.count ?? null)
      : null,
    pendingAlerts: canViewAlerts ? (alertsQuery.data?.count ?? null) : null,
    recentAlerts: alertsQuery.data?.results ?? [],
    errors: {
      cycles: cyclesQuery.error,
      enrolments: enrolmentsQuery.error,
      alerts: alertsQuery.error,
    },
    loading:
      loading ||
      cyclesQuery.loading ||
      enrolmentsQuery.loading ||
      alertsQuery.loading,
  };
}
