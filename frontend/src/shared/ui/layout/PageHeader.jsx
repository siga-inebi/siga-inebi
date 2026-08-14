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
    <Stack
      alignItems={{ xs: "flex-start", sm: "center" }}
      direction={{ xs: "column", sm: "row" }}
      gap={2}
      justifyContent="space-between"
      sx={{ mb: 3 }}
    >
      <Box sx={{ minWidth: 0 }}>
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
