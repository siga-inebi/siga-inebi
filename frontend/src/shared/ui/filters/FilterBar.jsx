import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";

/**
 * Barra de filtros de un listado: buscador + selects + acciones.
 *
 * Envuelve en un `Stack` con `flexWrap` para que en pantallas angostas los
 * controles bajen de linea en vez de comprimirse hasta ser inutilizables.
 *
 * @param {object}    props
 * @param {ReactNode} props.children  Controles de filtro.
 * @param {Function} [props.onClear]  Si se pasa, muestra el boton "Limpiar".
 * @param {ReactNode}[props.actions]  Acciones a la derecha (exportar, etc).
 */
export function FilterBar({ actions, children, onClear }) {
  return (
    <Stack
      alignItems={{ xs: "stretch", md: "center" }}
      direction={{ xs: "column", md: "row" }}
      gap={1.5}
      sx={{
        px: { xs: 1.5, md: 2 },
        py: 1.5,
        borderBottom: "1px solid",
        borderColor: "divider",
      }}
    >
      {children}
      {onClear ? (
        <Button onClick={onClear} size="small" variant="text">
          Limpiar
        </Button>
      ) : null}
      {actions ? (
        <Stack direction="row" gap={1} sx={{ ml: { md: "auto" } }}>
          {actions}
        </Stack>
      ) : null}
    </Stack>
  );
}
