import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { ThemeProvider } from "@mui/material/styles";
import { MemoryRouter } from "react-router-dom";

import { theme } from "@theme/theme.js";

/**
 * Renderiza con router y con el tema de la aplicacion.
 *
 * El `ThemeProvider` no es decoracion en los tests: los componentes del sistema
 * leen tokens propios (`palette.surfaces`, `tokens.radii`, `tokens.fonts`) que el
 * tema por defecto de MUI no trae. Sin el, cualquier `sx` que use un token revienta
 * con "cannot read properties of undefined" y el fallo no dice nada del
 * comportamiento que se estaba probando.
 *
 * El `QueryClient` es uno nuevo por llamada, no el singleton de la app: el de
 * la app cachea catalogos por minutos a proposito, lo que haria que el segundo
 * `test()` de un archivo viera datos del primero en vez del mock que acaba de
 * configurar. El `staleTime` se mantiene alto (igual que en produccion) y no
 * en cero: en cero, cualquier segunda suscripcion a la misma query durante el
 * mismo test (p.ej. un re-render mientras la primera peticion sigue en vuelo)
 * la marca "stale" de inmediato y react-query la vuelve a pedir — el mismo
 * ×2 que esta cache existe para eliminar, solo que disparado por el test.
 *
 * Se expone `queryClient` en el resultado para que un test pueda inspeccionar
 * la cache directamente (p.ej. confirmar que dos componentes comparten una
 * sola query) en vez de depender solo de contar llamadas al mock del servicio.
 */
export function renderWithRouter(ui, { route = "/" } = {}) {
  window.history.pushState({}, "Test page", route);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 60_000 } },
  });
  const result = render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
  result.queryClient = queryClient;
  return result;
}
