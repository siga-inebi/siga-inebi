/**
 * softTone.js — Helpers de tono suave reutilizables.
 *
 * Viven dentro de `shared/theme/` a proposito: son los unicos lugares fuera de
 * la paleta autorizados a calcular color, y lo hacen derivando del tema en
 * tiempo de render, asi funcionan igual en claro y en oscuro sin duplicar
 * tablas de color.
 *
 * Usan `toneAlpha` y no `alpha()` directo: con variables CSS activas, el color
 * del tema es un `var(--mui-palette-*)` y `alpha()` necesita un hex. Ver
 * `tokens/color.js` para el porque completo.
 */

import { palette, toneAlpha } from "./color.js";

/**
 * Fondo semitransparente + texto del mismo tono semantico.
 *
 * @param {object} theme     Tema MUI (de `useTheme()`).
 * @param {"primary"|"secondary"|"success"|"warning"|"error"|"info"} tone
 * @param {number} intensity Opacidad del fondo (default 0.12).
 */
export function softTone(theme, tone, intensity = 0.12) {
  return {
    bgcolor: toneAlpha(theme, tone, intensity),
    color: `${tone}.main`,
  };
}

/**
 * Overrides para el estado seleccionado de un chip o boton.
 *
 * Devuelve `{}` cuando no esta seleccionado para no pisar los defaults del
 * componente. El spread va SIEMPRE al final del `sx` — si va al principio, el
 * hover por defecto declarado despues le gana y el estado activo se pierde al
 * pasar el mouse.
 *
 * @param {object}  theme
 * @param {boolean} selected
 */
export function selectedToneSx(theme, selected) {
  if (!selected) return {};
  return {
    bgcolor: toneAlpha(theme, "primary", 0.1),
    borderColor: toneAlpha(theme, "primary", 0.4),
    "&:hover": {
      bgcolor: toneAlpha(theme, "primary", 0.18),
      borderColor: toneAlpha(theme, "primary", 0.55),
    },
    "&:active": {
      bgcolor: toneAlpha(theme, "primary", 0.25),
    },
    color: palette(theme).primary.main,
  };
}
