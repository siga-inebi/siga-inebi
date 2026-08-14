import { useCallback, useEffect, useMemo, useState } from "react";

/** Filas por pagina de los listados que se paginan en el cliente. */
export const LOCAL_PAGE_SIZE = 10;

/**
 * Listado que se trae completo y se filtra y pagina en memoria.
 *
 * Es el patron de los dominios cuyos endpoints REST todavia no existen y se
 * sirven desde un servicio con interruptor mock/real: el servicio devuelve el
 * arreglo entero, asi que filtrar y paginar del lado del cliente es lo unico
 * posible. Cuando el backend exponga paginacion real, estas pantallas cambian a
 * `usePaginatedList` y este hook desaparece — de ahi que el contrato que
 * devuelve sea deliberadamente parecido.
 *
 * @param {Function} loader           Devuelve una promesa con el arreglo completo.
 * @param {object}   options
 * @param {Function} options.matches  (item, consulta) => boolean. Filtro de busqueda.
 * @param {Function} [options.filters] (item) => boolean. Filtro adicional ya cerrado.
 * @param {number}   [options.pageSize]
 */
export function useLocalList(loader, { filters, matches, pageSize = LOCAL_PAGE_SIZE }) {
  const [all, setAll] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);

  useEffect(() => {
    let active = true;
    loader()
      .then((data) => {
        if (active) setAll(data);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [loader]);

  const query = search.trim().toLowerCase();

  const filtered = useMemo(() => {
    let rows = all;
    if (query) rows = rows.filter((item) => matches(item, query));
    if (filters) rows = rows.filter(filters);
    return rows;
  }, [all, filters, matches, query]);

  // La pagina se acota en render en vez de corregirse en un efecto: si el
  // filtro deja menos paginas que la actual, un efecto pintaria una tabla vacia
  // durante un frame antes de reponerse.
  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize));
  const currentPage = Math.min(page, pageCount - 1);
  const items = filtered.slice(currentPage * pageSize, (currentPage + 1) * pageSize);

  const changeSearch = useCallback((value) => {
    setSearch(value);
    setPage(0);
  }, []);

  /** Reemplaza un registro tras editarlo, sin volver a pedir el listado. */
  const replaceItem = useCallback((updated, isSame) => {
    setAll((current) => current.map((item) => (isSame(item) ? updated : item)));
  }, []);

  const addItem = useCallback((created) => {
    setAll((current) => [...current, created]);
  }, []);

  return {
    all,
    items,
    filtered,
    loading,
    error,
    search,
    setSearch: changeSearch,
    addItem,
    replaceItem,
    pagination: {
      page: currentPage,
      rowsPerPage: pageSize,
      total: filtered.length,
      onPageChange: setPage,
    },
  };
}
