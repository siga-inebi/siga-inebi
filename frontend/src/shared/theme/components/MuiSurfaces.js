/**
 * MuiSurfaces.js — Paper, Card, Dialog, Menu, Tooltip, Chip.
 *
 * Dos reglas de superficie del sistema:
 *   1. Lo asentado no tiene sombra: se define con borde hairline y espacio.
 *   2. Lo flotante si: ventanas modales, menus y popovers, con sombra amplia.
 *
 * Los formularios y el detalle de una entidad son VENTANAS CENTRADAS, no
 * paneles laterales (ver `FloatingWindow`).
 */

import { appRadii } from "../tokens/radii.js";
import { appElevations, appShadows } from "../tokens/shadows.js";
import { DISPLAY_STACK } from "../tokens/typography.js";
import { palette } from "../tokens/color.js";

export const MuiPaper = {
  defaultProps: { elevation: 0 },
  styleOverrides: {
    root: { backgroundImage: "none" },
    rounded: { borderRadius: appRadii.card },
    elevation1: { boxShadow: appElevations[1] },
    elevation2: { boxShadow: appElevations[2] },
    elevation3: { boxShadow: appElevations[3] },
  },
};

export const MuiCard = {
  defaultProps: { elevation: 0 },
  styleOverrides: {
    root: { borderRadius: appRadii.card, backgroundImage: "none" },
  },
};

export const MuiDialog = {
  defaultProps: { maxWidth: "sm", fullWidth: true },
  styleOverrides: {
    paper: ({ theme }) => ({
      borderRadius: appRadii.dialog,
      boxShadow: appShadows.window,
      border: "1px solid",
      borderColor: palette(theme).divider,
      backgroundImage: "none",
    }),
  },
};

export const MuiDialogTitle = {
  styleOverrides: {
    root: {
      fontFamily: DISPLAY_STACK,
      fontSize: "1.125rem",
      fontWeight: 600,
      padding: "1.25rem 1.5rem 0.5rem",
    },
  },
};

export const MuiBackdrop = {
  styleOverrides: {
    // El fondo se oscurece sin desenfoque: el desenfoque cuesta GPU y este
    // sistema debe correr en telefonos de gama baja.
    root: { backgroundColor: "rgba(15,27,38,0.42)" },
    invisible: { backgroundColor: "transparent" },
  },
};

export const MuiDrawer = {
  styleOverrides: {
    paper: { border: "none", backgroundImage: "none" },
  },
};

export const MuiMenu = {
  styleOverrides: {
    paper: ({ theme }) => ({
      borderRadius: appRadii.menu,
      boxShadow: appShadows.menu,
      border: "1px solid",
      borderColor: palette(theme).divider,
      minWidth: "10rem",
    }),
  },
};

export const MuiMenuItem = {
  styleOverrides: {
    root: { fontSize: "0.875rem" },
  },
};

export const MuiPopover = {
  styleOverrides: {
    paper: ({ theme }) => ({
      borderRadius: appRadii.menu,
      boxShadow: appShadows.popover,
      border: "1px solid",
      borderColor: palette(theme).divider,
    }),
  },
};

export const MuiTooltip = {
  defaultProps: { arrow: true },
  styleOverrides: {
    tooltip: ({ theme }) => ({
      fontSize: "0.75rem",
      borderRadius: appRadii.tooltip,
      backgroundColor: palette(theme).text.primary,
    }),
    arrow: ({ theme }) => ({ color: palette(theme).text.primary }),
  },
};

export const MuiChip = {
  styleOverrides: {
    root: { borderRadius: appRadii.chip, fontWeight: 600, letterSpacing: "0.01em" },
    sizeSmall: { height: "1.25rem", fontSize: "0.6875rem" },
  },
};

export const MuiDivider = {
  styleOverrides: {
    root: { borderColor: "var(--mui-palette-divider)" },
  },
};

export const MuiSkeleton = {
  defaultProps: { animation: "wave" },
};

export const MuiLink = {
  defaultProps: { underline: "hover" },
};

export const MuiAlert = {
  defaultProps: { variant: "outlined" },
  styleOverrides: {
    root: { borderRadius: appRadii.input, fontSize: "0.8125rem" },
  },
};
