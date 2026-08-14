import { useId } from "react";

import Box from "@mui/material/Box";
import Dialog from "@mui/material/Dialog";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import CloseIcon from "@mui/icons-material/Close";

import { WINDOW_WIDTH } from "./windowWidth.js";

/**
 * Ventana modal centrada. Es el overlay unico del sistema: formularios de alta y
 * edicion, detalle de entidad y confirmaciones.
 *
 * Se eligio ventana centrada y no panel lateral: el panel deslizante deja el
 * formulario pegado a un borde de la pantalla y, en monitores anchos, obliga a
 * mover la vista al extremo derecho para escribir. La ventana centrada pone el
 * foco donde el ojo ya esta y admite formularios de dos columnas sin quedar
 * angosta.
 *
 * Anatomia fija: cabecera (titulo + cerrar) -> cuerpo con scroll propio -> pie
 * opcional con acciones alineadas a la derecha. El cuerpo scrollea, no la
 * ventana: la cabecera y el pie quedan siempre visibles, asi el boton de
 * guardar no se va de pantalla en un formulario largo.
 *
 * @param {object}    props
 * @param {boolean}   props.open
 * @param {Function}  props.onClose
 * @param {string}    props.title
 * @param {string}   [props.description]
 * @param {number}   [props.width=WINDOW_WIDTH.compact]
 * @param {ReactNode}[props.footer]
 * @param {boolean}  [props.busy]  Marca el cuerpo como aria-busy.
 * @param {ReactNode} props.children
 */
export function FloatingWindow({
  busy = false,
  children,
  description,
  footer,
  onClose,
  open,
  title,
  width = WINDOW_WIDTH.compact,
}) {
  // El dialogo se nombra con su propio titulo: sin `aria-labelledby` el lector
  // de pantalla anuncia "dialogo" y nada mas.
  const titleId = useId();
  // El foco se limpia ANTES de desmontar: si un input de la ventana conserva el
  // foco al cerrarse, el navegador lo devuelve al body y la pagina salta al
  // inicio. El rAF deja que el blur se aplique antes de arrancar la animacion.
  const handleClose = () => {
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
    requestAnimationFrame(onClose);
  };

  return (
    <Dialog
      aria-labelledby={titleId}
      fullWidth={false}
      onClose={handleClose}
      open={open}
      slotProps={{
        paper: {
          sx: {
            width: { xs: "100%", sm: width },
            maxWidth: "100%",
            // Alto acotado al viewport para que el cuerpo scrollee por dentro
            // en vez de estirar la ventana fuera de la pantalla.
            maxHeight: { xs: "100dvh", sm: "min(88dvh, 46rem)" },
            m: { xs: 0, sm: 2 },
            // A pantalla completa en movil: una ventana flotante en 360px de
            // ancho deja margenes inutiles y campos comprimidos.
            height: { xs: "100dvh", sm: "auto" },
            borderRadius: { xs: 0, sm: undefined },
            display: "flex",
            flexDirection: "column",
          },
        },
      }}
    >
      <Stack
        alignItems="flex-start"
        direction="row"
        gap={1}
        justifyContent="space-between"
        sx={{
          px: 3,
          py: 2,
          borderBottom: "1px solid",
          borderColor: "divider",
          flexShrink: 0,
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          {/*
            Encabezado real, no texto con estilo de titulo: un dialogo sin
            heading deja al lector de pantalla anunciando "dialogo" sin decir de
            que, y es lo primero que necesita saber quien no ve la pantalla.
          */}
          <Typography
            id={titleId}
            component="h2"
            sx={(theme) => ({
              fontFamily: theme.tokens.fonts.display,
              fontSize: "1.0625rem",
              fontWeight: 600,
              lineHeight: 1.35,
            })}
          >
            {title}
          </Typography>
          {description ? (
            <Typography color="text.secondary" sx={{ mt: 0.5 }} variant="body2">
              {description}
            </Typography>
          ) : null}
        </Box>
        <IconButton aria-label="Cerrar" onClick={handleClose} size="small" sx={{ mt: -0.5 }}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Stack>

      <Box aria-busy={busy} sx={{ flex: 1, overflowY: "auto", px: 3, py: 2.5 }}>
        {children}
      </Box>

      {footer ? (
        <Stack
          direction="row"
          gap={1}
          justifyContent="flex-end"
          sx={{
            px: 3,
            py: 2,
            borderTop: "1px solid",
            borderColor: "divider",
            bgcolor: "background.default",
            flexShrink: 0,
          }}
        >
          {footer}
        </Stack>
      ) : null}
    </Dialog>
  );
}
