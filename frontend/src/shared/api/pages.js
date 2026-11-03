/**
 * Tamano de pagina para recorridos completos. Es el `max_page_size` del
 * backend (`StandardPagination`): cuatro veces menos peticiones que con la
 * pagina por defecto de 25.
 */
export const COLLECT_PAGE_SIZE = 100;

/**
 * Error explicito cuando un recorrido no puede terminar. Antes habia un tope
 * silencioso de 40 paginas (1 000 filas): con mas registros, el resto dejaba de
 * existir para la busqueda, la exportacion y los desplegables sin ningun aviso
 * (docs/ux-ui.md 1.1.3). Ahora no hay tope: si el backend no avanza, se dice.
 */
export class IncompleteListError extends Error {
  constructor(message, { loaded, total } = {}) {
    super(message);
    this.name = "IncompleteListError";
    this.loaded = loaded;
    this.total = total;
  }
}

/**
 * Recorre todas las paginas de un listado del backend y devuelve todas las filas.
 *
 * No trunca. El recorrido sigue `next` hasta el final; el unico corte es de
 * seguridad y es ruidoso: si una pagina llega vacia pero anuncia `next`, o si se
 * pidieron mas paginas de las que `count` justifica, se lanza
 * `IncompleteListError` en vez de devolver un listado parcial que parezca
 * completo.
 *
 * Uso previsto: exportaciones que la persona pide explicitamente (con
 * `onProgress` para mostrar avance) y catalogos acotados. Las pantallas de
 * listado usan `useServerList`, que pide solo la pagina visible.
 *
 * @param {(params: object) => Promise<{results: Array, next: ?string, count?: number}>} fetchPage
 * @param {object} [options]
 * @param {number} [options.pageSize=COLLECT_PAGE_SIZE] `page_size` enviado al backend; `null` no lo envia.
 * @param {(progress: {loaded: number, total: number}) => void} [options.onProgress]
 * @param {AbortSignal} [options.signal] Cancela el recorrido entre paginas.
 */
export async function collectAllPages(
  fetchPage,
  { pageSize = COLLECT_PAGE_SIZE, onProgress, signal } = {}
) {
  const collected = [];
  let pageLimit = Infinity;

  for (let page = 1; ; page += 1) {
    if (signal?.aborted) {
      throw new DOMException("Operación cancelada.", "AbortError");
    }
    const params = pageSize ? { page, page_size: pageSize } : { page };
    const payload = await fetchPage(params);
    const results = payload?.results ?? [];
    collected.push(...results);

    const total = Number.isFinite(payload?.count)
      ? payload.count
      : collected.length;
    onProgress?.({ loaded: collected.length, total });

    if (!payload?.next) {
      break;
    }
    if (results.length === 0) {
      throw new IncompleteListError(
        "El servidor anunció más resultados pero envió una página vacía; el listado quedó incompleto.",
        { loaded: collected.length, total }
      );
    }
    if (pageLimit === Infinity) {
      // Una pagina de holgura por si el conteo cambia durante el recorrido.
      pageLimit = Math.ceil(total / results.length) + 1;
    }
    if (page >= pageLimit) {
      throw new IncompleteListError(
        "El listado sigue creciendo mientras se recorre; vuelva a intentarlo.",
        { loaded: collected.length, total }
      );
    }
  }

  return collected;
}
