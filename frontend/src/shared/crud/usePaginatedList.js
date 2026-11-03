import { useCallback, useEffect, useState } from "react";

/** Tamano de pagina por defecto (`REST_FRAMEWORK.PAGE_SIZE` del backend). */
export const DEFAULT_PAGE_SIZE = 25;

/**
 * Estado de lectura compartido por todas las pantallas de catalogo.
 *
 * `loader` recibe `{ page, include_inactive }` y devuelve la respuesta paginada
 * del backend. Debe venir memorizado con `useCallback`: es la dependencia que
 * dispara la recarga, y una funcion nueva en cada render provocaria un bucle.
 *
 * `pageSize` se pasa por opcion en vez de importarse de un servicio concreto:
 * este hook lo usan cuatro modulos y no debe conocer a ninguno.
 *
 * La pagina no se reinicia cuando cambia el registro padre; las pantallas
 * remontan el panel hijo con `key` para que su estado nazca limpio.
 */
export function usePaginatedList(
  loader,
  { canIncludeInactive = true, pageSize = DEFAULT_PAGE_SIZE } = {}
) {
  const [items, setItems] = useState([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [token, setToken] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");

    loader({
      page,
      include_inactive: canIncludeInactive ? includeInactive : false,
    })
      .then((payload) => {
        if (!active) return;
        setItems(payload?.results || []);
        setCount(payload?.count || 0);
      })
      .catch((requestError) => {
        if (!active) return;
        setItems([]);
        setCount(0);
        setError(requestError.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [loader, page, includeInactive, canIncludeInactive, token]);

  const refresh = useCallback(() => setToken((value) => value + 1), []);

  const goToPage = useCallback(
    (next) => setPage((current) => (next > 0 ? next : current)),
    []
  );

  return {
    items,
    count,
    loading,
    error,
    page,
    pageSize,
    pageCount: Math.max(1, Math.ceil(count / pageSize)),
    goToPage,
    includeInactive,
    setIncludeInactive,
    refresh,
    /**
     * Contrato de paginacion que espera `DataTable`.
     *
     * El backend pagina en base 1 y `TablePagination` de MUI en base 0: la
     * conversion vive aqui, una sola vez, en vez de en cada pantalla.
     */
    pagination: {
      page: page - 1,
      rowsPerPage: pageSize,
      total: count,
      onPageChange: (zeroBased) => goToPage(zeroBased + 1),
    },
  };
}
