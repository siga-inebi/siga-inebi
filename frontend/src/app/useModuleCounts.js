import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";

/** El menu no necesita el numero exacto al segundo: bastan minutos de margen. */
const COUNTS_STALE_TIME = 5 * 60_000;

function useStudentsCount(enabled) {
  const { data } = useResourceQuery(
    queryKeys.students.list({}),
    () =>
      import("@students/studentsService.js").then((m) =>
        m.studentsService.listPage({})
      ),
    { enabled, staleTime: COUNTS_STALE_TIME }
  );
  return data?.count ?? null;
}

function useTeachersCount(enabled) {
  const { data } = useResourceQuery(
    queryKeys.teachers.list({}),
    () =>
      import("@teachers/teachersService.js").then((m) =>
        m.teachersService.listPage({})
      ),
    { enabled, staleTime: COUNTS_STALE_TIME }
  );
  return data?.count ?? null;
}

function useGuardiansCount(enabled) {
  const { data } = useResourceQuery(
    queryKeys.guardians.list({}),
    () =>
      import("@guardians/guardiansService.js").then((m) =>
        m.guardiansService.listPage({})
      ),
    { enabled, staleTime: COUNTS_STALE_TIME }
  );
  return data?.count ?? null;
}

/**
 * Conteos por modulo para los badges del menu lateral.
 *
 * Los servicios se importan de forma dinamica dentro de cada fetcher, no
 * arriba del archivo: son la unica razon por la que el shell tendria que
 * conocer los dominios, y un import estatico los arrastraria al chunk inicial
 * para pintar tres numeros que no son criticos para la primera pantalla.
 *
 * `PrivateLayout` (y por lo tanto este hook) se desmonta y remonta en cada
 * navegacion entre modulos, porque cada ruta privada envuelve su propio
 * layout en vez de compartir uno via `Outlet`. Antes eso significaba volver a
 * pedir los 3 catalogos completos en cada clic del menu; con `staleTime`
 * largo, ese remount es un cache-hit, no una peticion nueva.
 *
 * Un modulo que falla queda sin badge (`null`), no rompe el menu: el conteo es
 * informativo y su ausencia no debe impedir navegar.
 *
 * El numero sale del `count` de la respuesta paginada, no del largo de la
 * primera pagina: con 100 estudiantes el badge decia 25, que es el tamano de
 * pagina del backend y no una cantidad de nada.
 */
export function useModuleCounts(enabled) {
  return {
    alumnos: useStudentsCount(enabled),
    docentes: useTeachersCount(enabled),
    padres: useGuardiansCount(enabled),
  };
}
