/**
 * MuiTable.js — Densidad y jerarquia de tabla.
 *
 * El header usa fondo opaco propio (no `action.hover` translucido) porque en
 * modo `stickyHeader` un fondo semitransparente deja ver las filas pasando por
 * debajo al scrollear.
 */

export const MuiTableCell = {
  styleOverrides: {
    root: {
      borderBottom: "1px solid",
      borderColor: "var(--mui-palette-divider)",
    },
    head: ({ theme }) => ({
      backgroundColor: theme.palette.surfaces.tableHead,
      color: theme.palette.text.secondary,
      fontSize: "0.75rem",
      fontWeight: 500,
      letterSpacing: "0.4px",
      textTransform: "uppercase",
      whiteSpace: "nowrap",
      padding: "0.8rem 1.25rem",
      borderBottom: `2px solid ${theme.palette.divider}`,
    }),
    body: {
      fontSize: "0.8125rem",
      padding: "0.8125rem 1rem",
    },
  },
};

export const MuiTableRow = {
  styleOverrides: {
    root: ({ theme }) => ({
      transition: "background 0.12s",
      "&:hover": { backgroundColor: theme.palette.action.hover },
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
