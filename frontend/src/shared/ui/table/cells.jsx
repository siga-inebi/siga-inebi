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
      sx={(theme) => ({
        fontFamily: theme.tokens.fonts.mono,
        fontSize: "0.8125rem",
      })}
    >
      {value}
    </Typography>
  );
}

/** Texto de ausencia ("Sin registrar", "Sin vincular"). */
export function MutedCell({ children }) {
  return (
    <Typography
      color="text.disabled"
      component="span"
      sx={{ fontSize: "0.8125rem" }}
    >
      {children}
    </Typography>
  );
}

/**
 * Nombre del catalogo, con el identificador crudo como respaldo.
 *
 * Casi todo listado del sistema recibe UUIDs del backend y los pinta como el
 * nombre que la persona reconoce, contra un indice `value -> label`
 * (`labelIndex` de `@shared/catalogs`). El respaldo importa: un catalogo que
 * todavia carga, o un registro dado de baja que ya no figura en el, dejaria la
 * celda VACIA — y una fila sin datos se lee como un error del sistema, no como
 * "esto ya no existe". El identificador al menos es rastreable.
 *
 * Estaba reimplementada, identica, en seis pantallas.
 *
 * @param {object} props
 * @param {Map<string,string>} props.index Indice de etiquetas del catalogo.
 * @param {string} props.id               Identificador que viene del backend.
 */
export function NameCell({ index, id }) {
  const label = index.get(id);
  if (label) return label;
  return id ? <CodeCell value={id} /> : <MutedCell>—</MutedCell>;
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
