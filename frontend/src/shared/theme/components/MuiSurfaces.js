/**
 * MuiSurfaces.js — Paper, Card, Dialog, Drawer, Menu, Tooltip, Chip.
 *
 * Todas las superficies flotantes comparten el lenguaje "Flat 2.0": sombra
 * difusa + anillo hairline, en vez de bordes duros.
 */

import { appRadii } from "../tokens/radii.js";
import { appElevations, appShadows } from "../tokens/shadows.js";

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
    paper: {
      borderRadius: appRadii.dialog,
      boxShadow: appShadows.dialog,
    },
  },
};

export const MuiDialogTitle = {
  styleOverrides: {
    root: { fontSize: "1rem", fontWeight: 600, padding: "1.25rem 1.5rem 0.5rem" },
  },
};

export const MuiDrawer = {
  styleOverrides: {
    paper: { border: "none", backgroundImage: "none" },
  },
};

export const MuiMenu = {
  styleOverrides: {
    paper: {
      borderRadius: appRadii.menu,
      boxShadow: appShadows.menu,
      minWidth: "10rem",
    },
  },
};

export const MuiMenuItem = {
  styleOverrides: {
    root: { fontSize: "0.875rem" },
  },
};

export const MuiPopover = {
  styleOverrides: {
    paper: { borderRadius: appRadii.menu, boxShadow: appShadows.popover },
  },
};

export const MuiTooltip = {
  defaultProps: { arrow: true },
  styleOverrides: {
    tooltip: ({ theme }) => ({
      fontSize: "0.75rem",
      borderRadius: appRadii.tooltip,
      backgroundColor: theme.palette.text.primary,
    }),
    arrow: ({ theme }) => ({ color: theme.palette.text.primary }),
  },
};

export const MuiChip = {
  styleOverrides: {
    root: { borderRadius: appRadii.chip, fontWeight: 500 },
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
