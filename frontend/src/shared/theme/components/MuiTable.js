/**
 * MuiTable.js — Densidad y jerarquia de tabla.
 *
 * La cabecera NO lleva relleno de color: se distingue por la regla inferior de
 * 2px en color de marca y por el texto en versalitas espaciadas. Una banda gris
 * de cabecera es el recurso mas visto en todo back-office; la regla sola pesa
 * menos y lee como encabezado de tabla impresa, que es el registro visual de
 * este sistema.
 *
 * Cuando la tabla scrollea con `stickyHeader`, la cabecera necesita fondo opaco
 * o las filas se ven pasar por debajo: eso lo resuelve `DataTable` aplicando
 * `background.paper` solo en ese modo.
 */

import { palette } from "../tokens/color.js";

export const MuiTableCell = {
  styleOverrides: {
    root: {
      borderBottom: "1px solid",
      borderColor: "var(--mui-palette-divider)",
    },
    head: ({ theme }) => ({
      backgroundColor: palette(theme).surfaces.tableHead,
      color: palette(theme).text.secondary,
      fontSize: "0.6875rem",
      fontWeight: 700,
      letterSpacing: "0.09em",
      textTransform: "uppercase",
      whiteSpace: "nowrap",
      padding: "0.75rem 1rem",
      borderBottom: `2px solid ${palette(theme).surfaces.tableHeadRule}`,
    }),
    body: {
      fontSize: "0.8125rem",
      padding: "0.75rem 1rem",
    },
  },
};

export const MuiTableRow = {
  styleOverrides: {
    root: ({ theme }) => ({
      transition: "background 0.12s",
      "&:hover": { backgroundColor: palette(theme).action.hover },
      "&:last-of-type .MuiTableCell-body": { borderBottom: "none" },
    }),
  },
};

export const MuiTablePagination = {
  styleOverrides: {
    root: { fontSize: "0.8125rem", borderTop: "none" },
    selectLabel: { fontSize: "0.8125rem" },
    displayedRows: { fontSize: "0.8125rem" },
  },
};
