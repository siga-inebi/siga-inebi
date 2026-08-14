/**
 * MuiButton.js — Botones pill, sin elevacion, sin mayusculas sostenidas.
 *
 * `textTransform: none` y `fontWeight: 500` ya son globales aqui: repetirlos en
 * un `sx` de call site es ruido y la guia lo marca como no conforme.
 */

import { alpha } from "@mui/material/styles";

import { appRadii } from "../tokens/radii.js";

export const MuiButton = {
  defaultProps: {
    disableElevation: true,
  },
  styleOverrides: {
    root: {
      borderRadius: appRadii.button,
      padding: "0.4375rem 1.125rem",
      textTransform: "none",
      fontWeight: 500,
    },
    sizeSmall: {
      padding: "0.3rem 0.875rem",
      fontSize: "0.8125rem",
    },
    containedPrimary: ({ theme }) => ({
      boxShadow: `0 1px 4px ${alpha(theme.palette.primary.main, 0.3)}`,
      "&:hover": {
        boxShadow: `0 2px 10px ${alpha(theme.palette.primary.main, 0.4)}`,
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
    root: {
      textTransform: "none",
      fontWeight: 500,
      fontSize: "0.8125rem",
      borderRadius: appRadii.pill,
      padding: "0.25rem 0.875rem",
    },
  },
};
