import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

/**
 * Encabezado de una ruta completa.
 *
 * No confundir con el header de `SectionCard`: `PageHeader` titula la pagina,
 * `SectionCard` titula un bloque dentro de ella. Mezclarlos produce dos titulos
 * compitiendo por la misma jerarquia visual.
 *
 * @param {object}    props
 * @param {string}    props.title
 * @param {string}   [props.subtitle]
 * @param {ReactNode}[props.action]    Accion primaria, arriba a la derecha.
 * @param {ReactNode}[props.breadcrumb] Migaja opcional sobre el titulo.
 */
export function PageHeader({ action, breadcrumb, subtitle, title }) {
  return (
    // `flexWrap` y no solo `direction`: una pantalla puede llevar cinco acciones
    // en el encabezado (asistencia), y con las acciones sin encoger el titulo y
    // su descripcion quedaban comprimidos en una columna de dos palabras por
    // linea. Asi el bloque de acciones baja completo a la linea siguiente en vez
    // de estrangular al titulo.
    <Stack
      alignItems={{ xs: "flex-start", md: "center" }}
      direction="row"
      flexWrap="wrap"
      gap={2}
      justifyContent="space-between"
      sx={{ mb: 3 }}
    >
      <Box sx={{ flex: "1 1 22rem", minWidth: 0 }}>
        {breadcrumb ? (
          <Typography
            component="p"
            sx={{ color: "text.secondary", mb: 0.5 }}
            variant="overline"
          >
            {breadcrumb}
          </Typography>
        ) : null}
        <Typography fontWeight="bold" variant="h5">
          {title}
        </Typography>
        {subtitle ? (
          <Typography color="text.secondary" sx={{ mt: 0.5 }} variant="body2">
            {subtitle}
          </Typography>
        ) : null}
      </Box>
      {action ? <Box sx={{ flexShrink: 0 }}>{action}</Box> : null}
    </Stack>
  );
}
