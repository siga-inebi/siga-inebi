import Typography from "@mui/material/Typography";

import { StatusChip } from "@ui/display/StatusChip.jsx";

/**
 * Celdas de tabla que se repiten en todos los listados del sistema.
 *
 * Estan aqui para que "codigo" o "estado" se vean igual en sedes, cursos,
 * niveles y personas sin que cada pantalla vuelva a decidir tamano, familia y
 * color.
 */

/** Codigo o identificador tecnico: monoespaciado para poder compararlo de un ojo. */
export function CodeCell({ value }) {
  return (
    <Typography
      component="code"
      sx={{ fontFamily: "monospace", fontSize: "0.8125rem", letterSpacing: "0.02em" }}
    >
      {value}
    </Typography>
  );
}

/** Texto de ausencia ("Sin registrar", "Sin vincular"). */
export function MutedCell({ children }) {
  return (
    <Typography color="text.disabled" component="span" sx={{ fontSize: "0.8125rem" }}>
      {children}
    </Typography>
  );
}

/** Estado activo/desactivado de un registro de catalogo. */
export function ActiveCell({
  active,
  activeLabel = "Activo",
  inactiveLabel = "Desactivado",
}) {
  return (
    <StatusChip
      label={active ? activeLabel : inactiveLabel}
      variant={active ? "success" : "neutral"}
    />
  );
}

/** Valor booleano de dominio ("Principal: Si/No"). */
export function BooleanCell({ value }) {
  return value ? (
    <StatusChip label="Si" variant="primary" />
  ) : (
    <MutedCell>No</MutedCell>
  );
}
