/**
 * softTone.js — Helpers de tono suave reutilizables.
 *
 * Viven dentro de `shared/theme/` a proposito: son los unicos lugares fuera de
 * la paleta autorizados a calcular color, y lo hacen derivando del tema en
 * tiempo de render (nunca con literales), asi funcionan igual en claro y en
 * oscuro sin duplicar tablas de color.
 */

import { alpha } from "@mui/material/styles";

/**
 * Fondo semitransparente + texto del mismo tono semantico.
 *
 * @param {object} theme     Tema MUI (de `useTheme()`).
 * @param {"primary"|"secondary"|"success"|"warning"|"error"|"info"} tone
 * @param {number} intensity Opacidad del fondo (default 0.12).
 */
export function softTone(theme, tone, intensity = 0.12) {
  return {
    bgcolor: alpha(theme.palette[tone].main, intensity),
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
 * @param {object} theme     Tema MUI.
 * @param {boolean} selected Si el elemento esta activo.
 */
export function selectedToneSx(theme, selected) {
  if (!selected) return {};
  const p = theme.palette.primary.main;
  return {
    bgcolor: alpha(p, 0.1),
    borderColor: alpha(p, 0.4),
    "&:hover": {
      bgcolor: alpha(p, 0.18),
      borderColor: alpha(p, 0.55),
    },
    "&:active": {
      bgcolor: alpha(p, 0.25),
    },
  };
}
