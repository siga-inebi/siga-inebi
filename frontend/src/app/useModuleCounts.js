import { hasAnyPermission, MODULE_PERMISSIONS } from "@auth/permissions.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";

/**
 * El menu no necesita el numero exacto al segundo. La frescura despues de una
 * escritura la garantiza la invalidacion (toda mutacion en `/students/`,
 * `/teachers/` o `/students/guardians/` invalida estas keys); el `staleTime`
 * solo evita repetir la peticion en cada navegacion.
 */
const COUNTS_STALE_TIME = 5 * 60_000;

/** Una sola fila basta: lo que importa es `count`, no las filas. */
const COUNT_PARAMS = { page_size: 1 };

function useStudentsCount(enabled) {
  const { data, loading } = useResourceQuery(
    queryKeys.students.list(COUNT_PARAMS),
    () =>
      import("@students/studentsService.js").then((m) =>
        m.studentsService.listPage(COUNT_PARAMS)
      ),
    { enabled, staleTime: COUNTS_STALE_TIME }
  );
  return { count: data?.count ?? null, loading };
}

function useTeachersCount(enabled) {
  const { data, loading } = useResourceQuery(
    queryKeys.teachers.list(COUNT_PARAMS),
    () =>
      import("@teachers/teachersService.js").then((m) =>
        m.teachersService.listPage(COUNT_PARAMS)
      ),
    { enabled, staleTime: COUNTS_STALE_TIME }
  );
  return { count: data?.count ?? null, loading };
}

function useGuardiansCount(enabled) {
  const { data, loading } = useResourceQuery(
    queryKeys.guardians.list(COUNT_PARAMS),
    () =>
      import("@guardians/guardiansService.js").then((m) =>
        m.guardiansService.listPage(COUNT_PARAMS)
      ),
    { enabled, staleTime: COUNTS_STALE_TIME }
  );
  return { count: data?.count ?? null, loading };
}

/**
 * Conteos por modulo para los badges del menu lateral y las tarjetas del panel
 * (docs/ux-ui.md 1.7). Es la UNICA fuente de esos numeros: el panel reutiliza
 * estas mismas keys en vez de descargar los padrones completos para contar.
 *
 * Los servicios se importan de forma dinamica dentro de cada fetcher: son la
 * unica razon por la que el shell tendria que conocer los dominios, y un import
 * estatico los arrastraria al chunk inicial.
 *
 * Cada conteo se pide solo si la cuenta puede ver ese modulo: pedir el listado
 * de estudiantes sin permiso solo produce un 403 y un asiento de denegacion en
 * la bitacora en cada carga.
 *
 * Un modulo que falla queda sin badge (`null`), no rompe el menu.
 *
 * @param {boolean} enabled
 * @param {object} [user] Usuario de sesion; sin el no se pide nada.
 */
export function useModuleCountsState(enabled, user) {
  const allowed = Boolean(enabled && user);
  const alumnos = useStudentsCount(
    allowed && hasAnyPermission(user, MODULE_PERMISSIONS.alumnos)
  );
  const docentes = useTeachersCount(allowed);
  const padres = useGuardiansCount(allowed);
  return {
    counts: {
      alumnos: alumnos.count,
      docentes: docentes.count,
      padres: padres.count,
    },
    loading: alumnos.loading || docentes.loading || padres.loading,
  };
}

/** Solo los conteos, para los badges del menu. */
export function useModuleCounts(enabled, user) {
  return useModuleCountsState(enabled, user).counts;
}
