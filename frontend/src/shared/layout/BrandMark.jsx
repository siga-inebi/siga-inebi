import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import logo from "@shared/assets/logo.jpg";

/**
 * Logotipo + nombre del establecimiento.
 *
 * @param {object}  props
 * @param {boolean} [props.compact] Solo el logotipo (menu colapsado, movil).
 * @param {"small"|"large"} [props.size="small"]
 */
export function BrandMark({ compact = false, size = "small" }) {
  const box = size === "large" ? 56 : 34;

  return (
    <Stack alignItems="center" direction="row" gap={1.25} sx={{ minWidth: 0 }}>
      <Box
        alt="Logotipo del INEBI de Salcaja"
        component="img"
        src={logo}
        sx={(theme) => ({
          width: box,
          height: box,
          borderRadius: theme.tokens.radii.chip,
          objectFit: "cover",
          flexShrink: 0,
          // El anillo hairline separa el logo del fondo sin dibujarle un marco.
          boxShadow: theme.tokens.shadows.card,
        })}
      />
      {compact ? null : (
        <Box sx={{ minWidth: 0 }}>
          <Typography
            sx={{
              fontSize: size === "large" ? "1.25rem" : "0.9375rem",
              fontWeight: 700,
              letterSpacing: "-0.01em",
              lineHeight: 1.2,
            }}
          >
            SIGA-INEBI
          </Typography>
          <Typography
            sx={{
              fontSize: "0.75rem",
              color: "text.secondary",
              display: { xs: "none", sm: "block" },
            }}
          >
            Instituto Nacional de Educacion Basica de Salcaja
          </Typography>
        </Box>
      )}
    </Stack>
  );
}
