import Box from "@mui/material/Box";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";

/** Anchos estandarizados. Fuera de estos tres, justificar en el call site. */
export const DRAWER_WIDTH = {
  compact: 560,
  medium: 680,
  wide: 860,
};

/**
 * Overlay lateral. Es el overlay por defecto del sistema para formularios de
 * alta/edicion y para detalle de entidad.
 *
 * Se prefiere sobre un dialog centrado porque conserva la tabla visible detras:
 * el usuario no pierde el contexto de la fila que estaba mirando. Los dialogs
 * quedan para confirmaciones y microformularios (ver `ConfirmDialog`).
 *
 * @param {object}    props
 * @param {boolean}   props.open
 * @param {Function}  props.onClose
 * @param {string}    props.title
 * @param {string}   [props.description]
 * @param {number}   [props.width=DRAWER_WIDTH.compact]
 * @param {ReactNode}[props.footer]
 * @param {boolean}  [props.busy]  Marca el contenido como aria-busy.
 * @param {ReactNode} props.children
 */
export function BaseDrawer({
  busy = false,
  children,
  description,
  footer,
  onClose,
  open,
  title,
  width = DRAWER_WIDTH.compact,
}) {
  // El foco se limpia ANTES de desmontar: si un input del drawer conserva el
  // foco al cerrarse, el navegador lo devuelve al body y la pagina salta al
  // inicio. El rAF deja que el blur se aplique antes de arrancar la animacion.
  const handleClose = () => {
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
    requestAnimationFrame(onClose);
  };

  return (
    <Drawer
      anchor="right"
      onClose={handleClose}
      open={open}
      slotProps={{
        backdrop: { sx: { backdropFilter: "blur(2px)" } },
        paper: {
          sx: (theme) => ({
            width: { xs: "100%", sm: width },
            maxWidth: "100%",
            boxShadow: theme.tokens.shadows.drawerRight,
            display: "flex",
            flexDirection: "column",
          }),
        },
      }}
    >
      <Stack
        alignItems="center"
        direction="row"
        gap={1}
        justifyContent="space-between"
        sx={{ p: 2, borderBottom: "1px solid", borderColor: "divider", flexShrink: 0 }}
      >
        <Typography fontWeight={600} variant="h6">
          {title}
        </Typography>
        <IconButton aria-label="Cerrar" onClick={handleClose} size="small">
          <CloseIcon fontSize="small" />
        </IconButton>
      </Stack>

      <Box aria-busy={busy} sx={{ flex: 1, overflowY: "auto", p: 3 }}>
        {description ? (
          <Typography color="text.secondary" sx={{ mb: 3 }} variant="body2">
            {description}
          </Typography>
        ) : null}
        {children}
      </Box>

      {footer ? (
        <Stack
          direction="row"
          gap={2}
          justifyContent="flex-end"
          sx={{ p: 2, borderTop: "1px solid", borderColor: "divider", flexShrink: 0 }}
        >
          {footer}
        </Stack>
      ) : null}
    </Drawer>
  );
}
