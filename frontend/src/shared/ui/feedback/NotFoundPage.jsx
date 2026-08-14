import { Link as RouterLink } from "react-router-dom";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import SearchOffIcon from "@mui/icons-material/SearchOff";

import { SectionCard } from "@ui/layout/SectionCard.jsx";

export function NotFoundPage() {
  return (
    <SectionCard sx={{ maxWidth: 520, mx: "auto", mt: 6 }}>
      <Stack alignItems="center" gap={1.5} sx={{ px: 3, py: 5 }}>
        <SearchOffIcon sx={{ fontSize: "3rem", color: "text.disabled" }} />
        <Typography fontWeight={600} variant="h6">
          Pagina no encontrada
        </Typography>
        <Typography color="text.secondary" sx={{ textAlign: "center" }} variant="body2">
          La direccion que abriste no corresponde a ninguna seccion del sistema.
        </Typography>
        <Button component={RouterLink} sx={{ mt: 1 }} to="/" variant="contained">
          Ir al inicio
        </Button>
      </Stack>
    </SectionCard>
  );
}
