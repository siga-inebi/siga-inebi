import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { DEFAULT_ROWS_PER_PAGE_OPTIONS } from "@ui/table/tableOptions.js";

/** Tamano de pagina por defecto: el `page_size` de `StandardPagination`. */
export const SERVER_PAGE_SIZE = 25;

/** Espera tras la ultima tecla antes de pedir la busqueda al servidor. */
export const SEARCH_DEBOUNCE_MS = 300;

function toPositiveInt(value, fallback) {
  const number = Number.parseInt(value, 10);
  return Number.isFinite(number) && number > 0 ? number : fallback;
}

function compact(params) {
  return Object.fromEntries(
    Object.entries(params).filter(
      ([, value]) =>
        value !== undefined && value !== null && value !== "" && value !== false
    )
  );
}

/**
 * Hook unico de listado paginado en el servidor (docs/ux-ui.md 1.1).
 *
 * Reemplaza a `usePaginatedList` (pagina fija, estado en memoria) y al ya
 * eliminado `useLocalList` + `collectAllPages` (descarga del padron completo).
 * Pide solo la pagina visible y deja en la URL todo lo que define la vista:
 *
 *   ?page=2&page_size=50&search=ana&ordering=-last_login&status=active
 *
 * Asi volver atras, recargar o compartir el enlace conserva la vista. Con
 * `urlPrefix` dos listados conviven en la misma pantalla sin pisarse
 * (`?roles_page=2`).
 *
 * Devuelve el contrato que esperan `ListSection` y `DataTable`, y SIEMPRE
 * entrega `onRowsPerPageChange`: el selector "Filas por pagina" funciona.
 *
 * La busqueda espera `SEARCH_DEBOUNCE_MS` antes de pedir; cambiar busqueda,
 * filtros, orden o tamano vuelve a la pagina 1.
 *
 * @param {object} options
 * @param {Array}  options.queryKey  Prefijo de key (de `queryKeys.js`); se le agregan los parametros.
 * @param {(params: object) => Promise<{count:number, results:Array}>} options.fetchPage
 * @param {object} [options.defaultFilters] Filtros propios del dominio y su valor inicial.
 * @param {string} [options.defaultOrdering]
 * @param {number} [options.defaultPageSize=SERVER_PAGE_SIZE]
 * @param {number[]} [options.pageSizeOptions]
 * @param {boolean} [options.canIncludeInactive=false] Si el listado acepta `include_inactive`.
 * @param {string} [options.urlPrefix=""]
 * @param {boolean} [options.enabled=true]
 */
export function useServerList({
  queryKey,
  fetchPage,
  defaultFilters = {},
  defaultOrdering = "",
  defaultPageSize = SERVER_PAGE_SIZE,
  pageSizeOptions = DEFAULT_ROWS_PER_PAGE_OPTIONS,
  canIncludeInactive = false,
  urlPrefix = "",
  enabled = true,
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const param = useCallback((name) => `${urlPrefix}${name}`, [urlPrefix]);

  // Los filtros por defecto se leen una vez: un objeto literal nuevo en cada
  // render no debe volver a disparar nada.
  const defaultsRef = useRef(defaultFilters);
  const filterNames = Object.keys(defaultsRef.current);

  const page = toPositiveInt(searchParams.get(param("page")), 1);
  // Debe coincidir con el máximo de StandardPagination, incluso con una URL manual.
  const pageSize = Math.min(
    100,
    toPositiveInt(searchParams.get(param("page_size")), defaultPageSize)
  );
  const search = searchParams.get(param("search")) ?? "";
  const ordering = searchParams.get(param("ordering")) ?? defaultOrdering;
  const includeInactive =
    canIncludeInactive && searchParams.get(param("include_inactive")) === "1";
  const filtersKey = filterNames
    .map((name) => searchParams.get(param(name)) ?? "")
    .join("\u0000");
  const filters = useMemo(
    () =>
      Object.fromEntries(
        filterNames.map((name) => [
          name,
          searchParams.get(param(name)) ?? defaultsRef.current[name] ?? "",
        ])
      ),
    // filtersKey resume los valores de la URL que importan.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [filtersKey, param]
  );

  const update = useCallback(
    (changes, { resetPage = true } = {}) => {
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current);
          for (const [name, value] of Object.entries(changes)) {
            const key = param(name);
            if (value === undefined || value === null || value === "") {
              next.delete(key);
            } else {
              next.set(key, String(value));
            }
          }
          if (resetPage) next.delete(param("page"));
          return next;
        },
        { replace: true }
      );
    },
    [param, setSearchParams]
  );

  // Texto que se esta escribiendo; se confirma en la URL con espera.
  const [searchInput, setSearchInput] = useState(search);
  const lastCommitted = useRef(search);
  useEffect(() => {
    // Un cambio externo de la URL (atras/adelante) manda sobre lo escrito.
    if (search !== lastCommitted.current) {
      lastCommitted.current = search;
      setSearchInput(search);
    }
  }, [search]);
  useEffect(() => {
    if (searchInput === lastCommitted.current) return undefined;
    const timer = window.setTimeout(() => {
      lastCommitted.current = searchInput.trim() === "" ? "" : searchInput;
      update({ search: searchInput.trim() === "" ? "" : searchInput });
    }, SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [searchInput, update]);

  const params = useMemo(
    () =>
      compact({
        page,
        page_size: pageSize,
        search: search.trim(),
        ordering,
        include_inactive: includeInactive,
        ...filters,
      }),
    [page, pageSize, search, ordering, includeInactive, filters]
  );

  const query = useQuery({
    queryKey: [...queryKey, params],
    queryFn: () => fetchPage(params),
    enabled,
    placeholderData: keepPreviousData,
  });

  const count = query.data?.count ?? 0;
  const pageCount = Math.max(1, Math.ceil(count / pageSize));

  const goToPage = useCallback(
    (next) => update({ page: next > 1 ? next : "" }, { resetPage: false }),
    [update]
  );
  const setPageSize = useCallback(
    (size) => update({ page_size: size === defaultPageSize ? "" : size }),
    [defaultPageSize, update]
  );
  const setFilter = useCallback(
    (name, value) => update({ [name]: value }),
    [update]
  );
  const setFilters = useCallback((values) => update(values), [update]);
  const setOrdering = useCallback(
    (value) => update({ ordering: value === defaultOrdering ? "" : value }),
    [defaultOrdering, update]
  );
  const setIncludeInactive = useCallback(
    (value) => update({ include_inactive: value ? "1" : "" }),
    [update]
  );
  const { refetch } = query;
  const refresh = useCallback(() => refetch(), [refetch]);

  return {
    items: query.data?.results ?? [],
    count,
    loading: enabled && query.isPending,
    fetching: query.isFetching,
    error: query.error ? query.error.message : "",
    page,
    pageSize,
    pageCount,
    goToPage,
    setPageSize,
    search: searchInput,
    setSearch: setSearchInput,
    filters,
    setFilter,
    setFilters,
    ordering,
    setOrdering,
    includeInactive,
    setIncludeInactive,
    refresh,
    /** Parametros vigentes, sin pagina: la base de una exportacion completa. */
    exportParams: compact({
      search: search.trim(),
      ordering,
      include_inactive: includeInactive,
      ...filters,
    }),
    params,
    pagination: {
      page: page - 1,
      rowsPerPage: pageSize,
      total: count,
      onPageChange: (zeroBased) => goToPage(zeroBased + 1),
      onRowsPerPageChange: setPageSize,
      rowsPerPageOptions: pageSizeOptions,
    },
  };
}
