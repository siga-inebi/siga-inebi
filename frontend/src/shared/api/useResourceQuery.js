import { useQuery } from "@tanstack/react-query";

/**
 * Wrapper delgado sobre `useQuery` con la forma que ya esperan los hooks de
 * catalogos y listados de esta app (`{data, loading, error}`), en vez de la
 * forma nativa de react-query (`{data, isLoading, error: Error|null}`).
 *
 * Agregar un recurso cacheado nuevo es escribir un `key` y un `fetcher`, no
 * copiar el trio `useState(loading/error/data)` + `useEffect` que existia
 * antes en cada hook de catalogo por separado (abierto/cerrado: se extiende
 * agregando una entrada, no modificando ni duplicando esta funcion).
 *
 * @param {Array} key - Query key de `queryKeys.js`.
 * @param {() => Promise<any>} fetcher
 * @param {{enabled?: boolean, defaultData?: any, staleTime?: number}} [options]
 */
export function useResourceQuery(key, fetcher, options = {}) {
  const { enabled = true, defaultData = null, staleTime } = options;

  const query = useQuery({
    queryKey: key,
    queryFn: fetcher,
    enabled,
    ...(staleTime === undefined ? {} : { staleTime }),
  });

  return {
    data: query.data ?? defaultData,
    loading: enabled && query.isPending,
    error: query.error ? query.error.message : "",
  };
}
