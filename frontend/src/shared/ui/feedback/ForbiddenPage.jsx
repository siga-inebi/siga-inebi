import { Link as RouterLink } from "react-router-dom";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";

import { SectionCard } from "@ui/layout/SectionCard.jsx";

/**
 * Ruta privada sin el permiso que la habilita (docs/ux-ui.md 1.4).
 *
 * Se explica antes de que la persona choque con un 403 a mitad de una
 * operacion. Es presentacion: el backend sigue negando por su cuenta.
 *
 * @param {object} props
 * @param {string} [props.moduleLabel]
 */
export function ForbiddenPage({ moduleLabel }) {
  return (
    <SectionCard sx={{ maxWidth: 520, mx: "auto", mt: 6 }}>
      <Stack alignItems="center" gap={1.5} sx={{ px: 3, py: 5 }}>
        <LockOutlinedIcon sx={{ fontSize: "3rem", color: "text.disabled" }} />
        <Typography component="h1" fontWeight={600} variant="h6">
          Sin acceso
        </Typography>
        <Typography
          color="text.secondary"
          sx={{ textAlign: "center" }}
          variant="body2"
        >
          {moduleLabel
            ? `Su cuenta no tiene permiso para usar «${moduleLabel}».`
            : "Su cuenta no tiene permiso para usar esta sección."}{" "}
          Si lo necesita para su trabajo, pídalo a administración.
        </Typography>
        <Button
          component={RouterLink}
          sx={{ mt: 1 }}
          to="/app"
          variant="contained"
        >
          Volver al panel
        </Button>
      </Stack>
    </SectionCard>
  );
}
