import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

/**
 * Estado vacio canonico.
 *
 * Wording (guia, seccion 8): "No hay <entidad> registrad{o|a}s" para catalogos,
 * "Sin <cosa>" para sublistas dentro de un detalle, y "Sin datos para los
 * filtros seleccionados" cuando hay filtros aplicados. Un vacio por filtro y un
 * vacio por catalogo sin registros son problemas distintos y el usuario tiene
 * que poder distinguirlos sin adivinar.
 *
 * @param {object}    props
 * @param {ReactNode}[props.icon]
 * @param {string}    props.message
 * @param {ReactNode}[props.action]
 */
export function EmptyState({ action, icon, message }) {
  return (
    <Stack alignItems="center" gap={1.5} sx={{ py: 5, px: 2 }}>
      {icon ? (
        <Box
          aria-hidden
          sx={{
            color: "text.disabled",
            display: "flex",
            "& > svg": { fontSize: "3rem" },
          }}
        >
          {icon}
        </Box>
      ) : null}
      <Typography
        color="text.secondary"
        sx={{ maxWidth: "25rem", textAlign: "center" }}
        variant="body2"
      >
        {message}
      </Typography>
      {action}
    </Stack>
  );
}
