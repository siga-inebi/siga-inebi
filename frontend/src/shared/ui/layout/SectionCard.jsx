import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { alpha } from "@mui/material/styles";

import { FILL_HEIGHT_QUERY } from "@theme/tokens/fillHeight.js";

/**
 * Unidad de composicion dominante del sistema.
 *
 * La firma visual es la regla superior de 2.5px en color primario: es lo que
 * hace que un tablero de seis cards se lea como seis bloques y no como una
 * mancha de rectangulos blancos.
 *
 * @param {object}    props
 * @param {string}   [props.title]
 * @param {string}   [props.subtitle]  Se oculta en xs: en movil compite con el titulo.
 * @param {ReactNode}[props.action]    Accion de la seccion, arriba a la derecha.
 * @param {boolean}  [props.fillHeight] Activa el modo "un solo scroll" (ver fillHeight.js).
 * @param {boolean}  [props.accent=true] Regla superior de marca.
 * @param {object}   [props.sx]
 * @param {ReactNode} props.children
 */
export function SectionCard({
  accent = true,
  action,
  children,
  fillHeight = false,
  subtitle,
  sx,
  title,
}) {
  const hasHeader = Boolean(title || action);

  return (
    <Paper
      elevation={0}
      sx={(theme) => ({
        borderRadius: theme.tokens.radii.card,
        overflow: "hidden",
        border: "1px solid",
        borderColor: "divider",
        ...(accent
          ? { borderTop: `2.5px solid ${theme.palette.primary.main}` }
          : null),
        boxShadow: `0 1px 6px ${alpha(theme.palette.common.black, 0.06)}`,
        display: "flex",
        flexDirection: "column",
        ...(fillHeight
          ? {
              [FILL_HEIGHT_QUERY]: {
                height: "100%",
                flex: 1,
                minHeight: 0,
              },
            }
          : null),
        ...sx,
      })}
    >
      {hasHeader ? (
        <Stack
          alignItems="center"
          direction="row"
          gap={2}
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
            {title ? (
              <Typography
                component="h2"
                sx={{
                  fontSize: "0.9375rem",
                  fontWeight: 700,
                  letterSpacing: "-0.01em",
                }}
              >
                {title}
              </Typography>
            ) : null}
            {subtitle ? (
              <Typography
                sx={{
                  fontSize: "0.8125rem",
                  color: "text.secondary",
                  display: { xs: "none", sm: "block" },
                }}
              >
                {subtitle}
              </Typography>
            ) : null}
          </Box>
          {action ? <Box sx={{ flexShrink: 0 }}>{action}</Box> : null}
        </Stack>
      ) : null}
      {children}
    </Paper>
  );
}

/**
 * Contenedor del area de tabla dentro de una `SectionCard`.
 *
 * Es el eslabon intermedio de la cadena flex de `fillHeight`: sin el, la tabla
 * no sabe cuanto alto tiene disponible y vuelve a crecer sin limite.
 */
export function SectionTableArea({ children, sx }) {
  return (
    <Box
      sx={{
        p: { xs: 1, md: 1.5 },
        display: "flex",
        flexDirection: "column",
        flex: 1,
        minHeight: 0,
        ...sx,
      }}
    >
      {children}
    </Box>
  );
}
