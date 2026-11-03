import { alpha } from "@mui/material/styles";

/**
 * color.js — Como leer color del tema sin romper el modo oscuro.
 *
 * PROBLEMA REAL (no teorico): con `cssVariables` activo, `theme.palette.X` NO
 * devuelve el color del esquema activo, sino el valor resuelto del esquema por
 * defecto. Emotion lo hornea en la clase CSS, asi que un `sx` que lee
 * `theme.palette.surfaces.sunken` pinta el color CLARO tambien en modo oscuro.
 * Se detecto con el item activo del menu lateral: en oscuro salia con fondo
 * hueso y texto casi invisible.
 *
 * SOLUCION: leer siempre desde `theme.vars`, que expone `var(--mui-palette-*)`
 * y por lo tanto sigue al esquema activo. `theme.vars` no existe cuando las
 * variables CSS estan apagadas (p.ej. en algun test), de ahi el fallback.
 *
 * REGLA DE LA CASA: dentro de `sx` o de `styleOverrides`, nunca `theme.palette`
 * a secas. O se usa una ruta en texto (`sx={{ color: "text.secondary" }}`), que
 * MUI ya resuelve por variable, o se usa `palette(theme)` de este archivo.
 */
export function palette(theme) {
  return (theme.vars ?? theme).palette;
}

/**
 * Color semantico con transparencia.
 *
 * `alpha()` no sirve sobre `var(--mui-palette-primary-main)`: necesita un hex.
 * Para eso MUI genera tokens de canal (`primary-mainChannel` = "28 43 58"), que
 * si admiten opacidad en notacion moderna `rgb(R G B / A)`.
 *
 * @param {object} theme
 * @param {"primary"|"secondary"|"success"|"warning"|"error"|"info"} tone
 * @param {number} opacity
 */
export function toneAlpha(theme, tone, opacity) {
  const channel = theme.vars?.palette?.[tone]?.mainChannel;
  if (channel) return `rgba(${channel} / ${opacity})`;
  return alpha(theme.palette[tone].main, opacity);
}
