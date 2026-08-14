import { memo } from "react";

import Box from "@mui/material/Box";
import Skeleton from "@mui/material/Skeleton";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TablePagination from "@mui/material/TablePagination";
import TableRow from "@mui/material/TableRow";

import { EmptyState } from "@ui/feedback/EmptyState.jsx";
import {
  FILL_HEIGHT_QUERY,
  TABLE_FALLBACK_MAX_HEIGHT,
} from "@theme/tokens/fillHeight.js";

/** Filas de esqueleto durante la primera carga. */
const SKELETON_ROWS = 5;

/**
 * Anchos deterministas del esqueleto. Un ancho aleatorio cambiaria en cada
 * render y produciria un parpadeo peor que el propio estado de carga.
 */
const SKELETON_WIDTHS = ["78%", "62%", "85%", "55%", "70%"];

const BODY_CELL_SX = { px: 2, py: 1.5 };

/** Nombres accesibles de los botones de paginacion, en espanol. */
const PAGINATION_LABELS = {
  first: "Primera pagina",
  last: "Ultima pagina",
  next: "Siguiente",
  previous: "Anterior",
};

const CLICKABLE_ROW_SX = {
  cursor: "pointer",
  "&:hover": { bgcolor: "action.hover" },
};

const DataTableRow = memo(function DataTableRow({ columns, onRowClick, row }) {
  return (
    <TableRow
      hover={Boolean(onRowClick)}
      onClick={onRowClick ? () => onRowClick(row) : undefined}
      sx={onRowClick ? CLICKABLE_ROW_SX : undefined}
    >
      {columns.map((column) => (
        <TableCell align={column.align} key={column.key} sx={BODY_CELL_SX}>
          {column.render ? column.render(row) : String(row[column.key] ?? "—")}
        </TableCell>
      ))}
    </TableRow>
  );
});

/**
 * Unico componente de tabla del sistema.
 *
 * @param {object}   props
 * @param {Array<{key:string,label:string,align?:string,render?:Function}>} props.columns
 * @param {Array<object>} props.rows
 * @param {boolean} [props.loading]
 * @param {string}  [props.emptyMessage="No hay datos disponibles"]
 * @param {object}  [props.pagination] {page (0-based), rowsPerPage, total, onPageChange, onRowsPerPageChange?, rowsPerPageOptions?}
 * @param {Function}[props.getRowKey]
 * @param {Function}[props.onRowClick]
 * @param {boolean} [props.fillHeight] Header pegado y paginacion anclada fuera del scroll.
 */
export function DataTable({
  columns,
  emptyMessage = "No hay datos disponibles",
  fillHeight = false,
  getRowKey,
  loading = false,
  onRowClick,
  pagination,
  rows,
}) {
  const hasRows = rows.length > 0;
  // El header solo se pega cuando el contenedor scrollea por dentro; si
  // scrollea la pagina, `sticky` lo dejaria flotando sobre otro contenido.
  const stickyHeader = fillHeight;

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        ...(fillHeight
          ? { [FILL_HEIGHT_QUERY]: { flex: 1, minHeight: 0 } }
          : null),
      }}
    >
      <TableContainer
        sx={{
          overflow: "auto",
          maxHeight: TABLE_FALLBACK_MAX_HEIGHT,
          ...(fillHeight
            ? {
                [FILL_HEIGHT_QUERY]: {
                  flex: 1,
                  minHeight: 0,
                  maxHeight: "none",
                },
              }
            : null),
        }}
      >
        <Table aria-busy={loading} size="small" stickyHeader={stickyHeader}>
          <TableHead>
            <TableRow>
              {columns.map((column) => (
                <TableCell
                  align={column.align}
                  key={column.key}
                  // La cabecera del sistema no lleva relleno de color, pero en
                  // modo pegado necesita fondo opaco o las filas se ven pasar
                  // por debajo al scrollear.
                  sx={
                    stickyHeader ? { bgcolor: "background.paper" } : undefined
                  }
                >
                  {column.label}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading
              ? Array.from({ length: SKELETON_ROWS }, (_, rowIndex) => (
                  <TableRow key={`skeleton-${rowIndex}`}>
                    {columns.map((column, columnIndex) => (
                      <TableCell key={column.key} sx={BODY_CELL_SX}>
                        <Skeleton
                          aria-hidden
                          variant="text"
                          width={
                            SKELETON_WIDTHS[
                              (rowIndex + columnIndex) % SKELETON_WIDTHS.length
                            ]
                          }
                        />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              : null}

            {!loading && !hasRows ? (
              <TableRow sx={{ "&:hover": { bgcolor: "transparent" } }}>
                <TableCell
                  colSpan={columns.length}
                  sx={{ borderBottom: "none" }}
                >
                  <EmptyState message={emptyMessage} />
                </TableCell>
              </TableRow>
            ) : null}

            {!loading
              ? rows.map((row, index) => (
                  <DataTableRow
                    columns={columns}
                    key={getRowKey ? getRowKey(row) : (row.id ?? index)}
                    onRowClick={onRowClick}
                    row={row}
                  />
                ))
              : null}
          </TableBody>
        </Table>
      </TableContainer>

      {pagination ? (
        <TablePagination
          component="div"
          count={pagination.total}
          // Los botones de pagina de MUI vienen con nombre accesible en ingles
          // ("Go to next page"): en una interfaz en espanol eso obliga al lector
          // de pantalla a cambiar de idioma a media tabla.
          getItemAriaLabel={(type) => PAGINATION_LABELS[type] ?? type}
          labelDisplayedRows={({ count, from, to }) =>
            `Mostrando ${from}–${to} de ${count}`
          }
          labelRowsPerPage="Filas por pagina:"
          onPageChange={(_event, page) => pagination.onPageChange(page)}
          onRowsPerPageChange={
            pagination.onRowsPerPageChange
              ? (event) =>
                  pagination.onRowsPerPageChange(Number(event.target.value))
              : undefined
          }
          page={pagination.page}
          rowsPerPage={pagination.rowsPerPage}
          rowsPerPageOptions={
            pagination.rowsPerPageOptions ?? [10, 25, 50, 100]
          }
          sx={{ flexShrink: 0, borderTop: "1px solid", borderColor: "divider" }}
        />
      ) : null}
    </Box>
  );
}
