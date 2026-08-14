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

import { appFonts, BODY_FONT, DISPLAY_STACK } from "./tokens/typography.js";
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
    // Dos familias con roles fijos: sans para todo lo operativo (leer datos,
    // llenar campos) y serif SOLO para titulos. El serif es lo que hace que la
    // pantalla se lea como un documento del establecimiento y no como un panel
    // corporativo; usarlo tambien en el cuerpo lo volveria pesado de leer en
    // tablas densas.
    fontFamily: `"${BODY_FONT}", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`,
    // Todo el texto se dimensiona en rem para que la escala de accesibilidad
    // del navegador funcione; px congelaria el tamano.
    fontSize: 14,
    h4: {
      fontFamily: DISPLAY_STACK,
      fontWeight: 600,
      letterSpacing: "-0.01em",
    },
    h5: {
      fontFamily: DISPLAY_STACK,
      fontWeight: 600,
      letterSpacing: "-0.01em",
    },
    h6: { fontFamily: DISPLAY_STACK, fontWeight: 600 },
    subtitle1: { fontWeight: 500 },
    subtitle2: { fontWeight: 600 },
    body2: { fontSize: "0.875rem" },
    button: { textTransform: "none", fontWeight: 500, letterSpacing: "0.01em" },
    overline: {
      fontSize: "0.6875rem",
      fontWeight: 600,
      letterSpacing: "0.1em",
      lineHeight: 2,
    },
  },

  // Radio global bajo: el lenguaje de forma del sistema es casi recto.
  shape: { borderRadius: 8 },

  // Tokens propios, accesibles como `theme.tokens.*` desde cualquier `sx`.
  tokens: {
    shadows: appShadows,
    radii: appRadii,
    fonts: appFonts,
  },

  components: appComponents,
});
