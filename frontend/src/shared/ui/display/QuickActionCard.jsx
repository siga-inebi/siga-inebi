import { Link as RouterLink } from "react-router-dom";

import ButtonBase from "@mui/material/ButtonBase";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { palette } from "@theme/tokens/color.js";

/**
 * Acceso rapido del panel: titulo, descripcion y navegacion a una ruta.
 *
 * Se construye sobre `ButtonBase` para que sea un destino de teclado real con
 * ripple y `focus-visible`, en vez de un `div` con `onClick` que el tabulador
 * no alcanza.
 *
 * @param {object} props
 * @param {string} props.title
 * @param {string} props.description
 * @param {string} props.to
 * @param {Function}[props.onPointerEnter] Gancho para precargar el chunk destino.
 */
export function QuickActionCard({ description, onPointerEnter, title, to }) {
  return (
    <ButtonBase
      component={RouterLink}
      onFocus={onPointerEnter}
      onPointerEnter={onPointerEnter}
      sx={(theme) => ({
        display: "block",
        textAlign: "left",
        width: "100%",
        height: "100%",
        px: 2.5,
        py: 2,
        borderRadius: theme.tokens.radii.card,
        border: "1px solid",
        borderColor: "divider",
        // Marcador dorado: la misma firma que el encabezado de seccion.
        borderLeft: `3px solid ${palette(theme).surfaces.sectionMarker}`,
        bgcolor: "background.paper",
        transition: "background-color 0.15s, border-color 0.15s",
        // Sin sombra al pasar el mouse: la respuesta es el fondo hundido, igual
        // que en las filas de tabla, para que la interfaz tenga un solo idioma.
        "&:hover": {
          bgcolor: palette(theme).surfaces.sunken,
          borderColor: palette(theme).text.disabled,
          borderLeftColor: palette(theme).surfaces.sectionMarker,
        },
      })}
      to={to}
    >
      <Stack gap={0.5}>
        <Typography sx={{ fontSize: "0.875rem", fontWeight: 700 }}>
          {title}
        </Typography>
        <Typography color="text.secondary" sx={{ fontSize: "0.8125rem" }}>
          {description}
        </Typography>
      </Stack>
    </ButtonBase>
  );
}
