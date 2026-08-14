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
 */
export function renderWithRouter(ui, { route = "/" } = {}) {
  window.history.pushState({}, "Test page", route);
  return render(
    <ThemeProvider theme={theme}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </ThemeProvider>
  );
}
