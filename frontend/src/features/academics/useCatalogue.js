import { useCallback, useEffect, useState } from "react";

import { PAGE_SIZE } from "../../services/academicsService.js";

/**
 * Estado de lectura compartido por todas las pantallas del catalogo.
 *
 * `loader` recibe `{ page, include_inactive }` y devuelve la respuesta paginada
 * del backend. Debe venir memorizado con `useCallback`: es la dependencia que
 * dispara la recarga.
 *
 * La pagina no se reinicia cuando cambia el registro padre; las pantallas
 * remontan el panel hijo con `key` para que su estado nazca limpio.
 */
export function useCatalogue(loader, { canIncludeInactive = true } = {}) {
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
        if (!active) {
          return;
        }
        setItems(payload?.results || []);
        setCount(payload?.count || 0);
      })
      .catch((requestError) => {
        if (!active) {
          return;
        }
        setItems([]);
        setCount(0);
        setError(requestError.message);
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
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
    pageCount: Math.max(1, Math.ceil(count / PAGE_SIZE)),
    goToPage,
    includeInactive,
    setIncludeInactive,
    refresh,
  };
}
