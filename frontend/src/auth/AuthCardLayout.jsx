import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { BrandMark } from "@layout/BrandMark.jsx";
import { ColorModeToggle } from "@layout/ColorModeToggle.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";

/**
 * Marco de las pantallas publicas de acceso: iniciar sesion, activar la cuenta
 * y restablecer la contraseña. Una sola composicion para que las tres se lean
 * como parte del mismo flujo.
 */
export function AuthCardLayout({ children, footer }) {
  return (
    <Box
      sx={{
        minHeight: "100dvh",
        bgcolor: "background.default",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        px: 2,
        py: 6,
      }}
    >
      <Box sx={{ width: "100%", maxWidth: 440 }}>
        <Stack alignItems="center" gap={2} sx={{ mb: 3 }}>
          <BrandMark compact size="large" />
          <Box sx={{ textAlign: "center" }}>
            <Typography fontWeight="bold" variant="h5">
              SIGA-INEBI
            </Typography>
            <Typography color="text.secondary" variant="body2">
              Instituto Nacional de Educación Básica de Salcajá
            </Typography>
          </Box>
        </Stack>

        <SectionCard>
          <Box sx={{ p: 3 }}>{children}</Box>
        </SectionCard>

        <Stack alignItems="center" gap={1.5} sx={{ mt: 3 }}>
          {footer}
          <ColorModeToggle />
          <Typography
            color="text.secondary"
            sx={{ textAlign: "center" }}
            variant="body2"
          >
            Uso institucional. Los accesos quedan registrados.
          </Typography>
        </Stack>
      </Box>
    </Box>
  );
}
