import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";

/**
 * Bajo este largo no se pide nada: una o dos letras sueltas devolverian casi
 * todo el catalogo, que es justo lo que la busqueda server-side existe para
 * evitar.
 */
const MIN_SEARCH_LENGTH = 2;

/**
 * Catalogo que se resuelve pidiendo al backend `?search=`, en vez de traer el
 * listado completo para filtrar en el cliente.
 *
 * Recibe `fetchPage` (la funcion `listPage` del servicio, que ya acepta
 * parametros de query) y `mapResult` (como mapear cada fila a
 * `{value,label}`, igual que los catalogos de `academicCatalogs.js`) como
 * parametros en vez de conocer una entidad concreta: agregar un picker
 * buscable para otra entidad es pasar estos dos argumentos, no escribir un
 * hook nuevo. `name` identifica la entidad en la query key (p.ej.
 * `"students"`) para que la cache de esta busqueda no colisione con la del
 * catalogo completo de la misma entidad.
 *
 * Solo se pide la primera pagina: una busqueda de texto ya acota el
 * resultado, y un picker no necesita mas de una pantalla de coincidencias
 * para que la persona afine lo que escribio.
 *
 * @param {string} name
 * @param {(params: object) => Promise<{results: Array}>} fetchPage
 * @param {(row: object) => {value: string, label: string}} mapResult
 * @param {string} term
 */
export function useSearchableCatalog(name, fetchPage, mapResult, term) {
  const trimmed = (term ?? "").trim();
  const ready = trimmed.length >= MIN_SEARCH_LENGTH;

  const { data, loading, error } = useResourceQuery(
    queryKeys.search(name, trimmed),
    () => fetchPage({ search: trimmed }),
    { enabled: ready, defaultData: null }
  );

  return {
    options: ready ? (data?.results ?? []).map(mapResult) : [],
    loading: ready && loading,
    error,
    ready,
  };
}
