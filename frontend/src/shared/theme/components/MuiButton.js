/**
 * MuiButton.js — Botones rectangulares, sin elevacion, sin mayusculas.
 *
 * `textTransform: none` y `fontWeight: 500` ya son globales aqui: repetirlos en
 * un `sx` de call site es ruido.
 *
 * El primario NO lleva sombra de color. Un boton que proyecta un halo de su
 * propio tono se ve como un boton de aplicacion de consumo; aqui la accion
 * primaria se distingue por ser la unica superficie rellena de la pantalla.
 */

import { palette, toneAlpha } from "../tokens/color.js";
import { appRadii } from "../tokens/radii.js";

export const MuiButton = {
  defaultProps: {
    disableElevation: true,
  },
  styleOverrides: {
    root: {
      borderRadius: appRadii.button,
      padding: "0.4375rem 1rem",
      textTransform: "none",
      fontWeight: 500,
      boxShadow: "none",
      "&:hover": { boxShadow: "none" },
    },
    sizeSmall: {
      padding: "0.3125rem 0.75rem",
      fontSize: "0.8125rem",
    },
    outlined: ({ theme }) => ({
      borderColor: palette(theme).divider,
      color: palette(theme).text.primary,
      "&:hover": {
        borderColor: palette(theme).text.secondary,
        backgroundColor: palette(theme).action.hover,
      },
    }),
  },
};

export const MuiIconButton = {
  styleOverrides: {
    root: {
      borderRadius: appRadii.input,
    },
  },
};

export const MuiToggleButton = {
  styleOverrides: {
    root: ({ theme }) => ({
      textTransform: "none",
      fontWeight: 500,
      fontSize: "0.8125rem",
      borderRadius: appRadii.button,
      padding: "0.25rem 0.625rem",
      borderColor: palette(theme).divider,
      "&.Mui-selected": {
        backgroundColor: toneAlpha(theme, "primary", 0.12),
        color: palette(theme).primary.main,
      },
    }),
  },
};
