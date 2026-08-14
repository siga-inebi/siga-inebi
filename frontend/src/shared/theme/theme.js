/**
 * theme.js — Punto de entrada del tema. Un solo `createTheme()`.
 *
 * Para cambiar la identidad visual del sistema:
 *   - marca / color primario -> `palette/brand.js` (constante `ACTIVE_BRAND`)
 *   - cualquier color        -> `palette/raw.js`
 *   - sombras y radios       -> `tokens/shadows.js`, `tokens/radii.js`
 *   - estilo de un componente-> `components/Mui*.js`
 *
 * Ningun componente de la aplicacion deberia necesitar tocarse para un cambio
 * de look: esa es la prueba de que el tema esta bien puesto.
 */

import { createTheme } from "@mui/material/styles";

import { appComponents } from "./components/index.js";
import { darkPalette } from "./palette/dark.js";
import { lightPalette } from "./palette/light.js";
import { appRadii } from "./tokens/radii.js";
import { appShadows } from "./tokens/shadows.js";

export const theme = createTheme({
  // CSS theme variables: el cambio claro/oscuro reemplaza variables CSS en
  // lugar de re-renderizar el arbol de React.
  cssVariables: { colorSchemeSelector: "class" },

  colorSchemes: {
    light: { palette: lightPalette },
    dark: { palette: darkPalette },
  },

  typography: {
    fontFamily:
      '"DM Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    // Todo el texto se dimensiona en rem para que la escala de accesibilidad
    // del navegador funcione; px congelaria el tamano.
    fontSize: 14,
    h4: { fontWeight: 700 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
    subtitle1: { fontWeight: 500 },
    subtitle2: { fontWeight: 600 },
    body2: { fontSize: "0.875rem" },
    button: { textTransform: "none", fontWeight: 500 },
    overline: {
      fontSize: "0.65rem",
      fontWeight: 600,
      letterSpacing: "0.08em",
      lineHeight: 2,
    },
  },

  shape: { borderRadius: 12 },

  // Tokens propios, accesibles como `theme.tokens.*` desde cualquier `sx`.
  tokens: {
    shadows: appShadows,
    radii: appRadii,
  },

  components: appComponents,
});
