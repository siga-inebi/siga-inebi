import { QueryClient } from "@tanstack/react-query";

/**
 * Instancia unica de cache compartida por toda la app.
 *
 * `staleTime` no es cero a proposito: los catalogos y contadores que migran a
 * esta capa se comportaban antes como "se cargan una vez por pantalla". Un
 * `staleTime` de cero convertiria cada montaje de componente en un refetch de
 * fondo, que es exactamente el patron que esta capa existe para eliminar.
 *
 * `refetchOnWindowFocus` queda apagado por la misma razon: nadie espera que
 * volver a la pestana dispare peticiones nuevas para un catalogo de secciones.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
      retry: false,
    },
  },
});
