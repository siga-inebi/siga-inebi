import { useId } from "react";

import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { FILL_HEIGHT_QUERY } from "@theme/tokens/fillHeight.js";
import { palette } from "@theme/tokens/color.js";

/**
 * Unidad de composicion dominante del sistema.
 *
 * Firma visual: un MARCADOR DORADO de 3px a la izquierda del titulo de seccion,
 * mas borde hairline y CERO sombra. Deliberadamente no lleva una regla de color
 * cruzando el borde superior: esa marca pertenece a otro producto, y aqui el
 * acento va donde esta la informacion (el titulo), no en el marco.
 *
 * @param {object}    props
 * @param {string}   [props.title]
 * @param {string}   [props.subtitle]   Se oculta en xs: en movil compite con el titulo.
 * @param {ReactNode}[props.action]     Accion de la seccion, arriba a la derecha.
 * @param {boolean}  [props.fillHeight] Activa el modo "un solo scroll" (ver fillHeight.js).
 * @param {boolean}  [props.marker=true] Marcador dorado junto al titulo.
 * @param {object}   [props.sx]
 * @param {ReactNode} props.children
 */
export function SectionCard({
  action,
  children,
  fillHeight = false,
  marker = true,
  subtitle,
  sx,
  title,
}) {
  const hasHeader = Boolean(title || action);
  const titleId = useId();

  return (
    <Paper
      // Cada seccion titulada es una region con nombre: en una pantalla con
      // cinco o seis bloques, eso permite saltar de uno a otro con el lector de
      // pantalla en vez de recorrerlos linealmente.
      aria-labelledby={title ? titleId : undefined}
      component={title ? "section" : "div"}
      elevation={0}
      sx={(theme) => ({
        borderRadius: theme.tokens.radii.card,
        overflow: "hidden",
        border: "1px solid",
        borderColor: "divider",
        boxShadow: "none",
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
          <Stack alignItems="stretch" direction="row" gap={1.5} sx={{ minWidth: 0 }}>
            {marker && title ? (
              <Box
                aria-hidden
                sx={(theme) => ({
                  width: 3,
                  borderRadius: 0.5,
                  backgroundColor: palette(theme).surfaces.sectionMarker,
                  flexShrink: 0,
                })}
              />
            ) : null}
            <Box sx={{ minWidth: 0 }}>
              {title ? (
                <Typography
                  id={titleId}
                  component="h2"
                  sx={(theme) => ({
                    fontFamily: theme.tokens.fonts.display,
                    fontSize: "1.0625rem",
                    fontWeight: 600,
                    lineHeight: 1.3,
                  })}
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
          </Stack>
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
