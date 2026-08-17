import { useEffect, useState } from "react";

import { collectAllPages } from "./collectAllPages.js";

/**
 * Todas las filas de un listado paginado, para alimentar un selector.
 *
 * `loader` recibe el numero de pagina y debe venir memorizado con `useCallback`.
 * `reloadToken` es el otro disparador: cambiarlo relee sin tocar el loader.
 */
export function useAllPages(loader, reloadToken = 0) {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");

    collectAllPages(loader)
      .then((collected) => {
        if (active) {
          setItems(collected);
        }
      })
      .catch((requestError) => {
        if (active) {
          setItems([]);
          setError(requestError.message);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [loader, reloadToken]);

  return { items, error, loading };
}
