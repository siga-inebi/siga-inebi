import { useState } from "react";
import { Link as RouterLink, useSearchParams } from "react-router-dom";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { authService } from "@auth/authService.js";
import { fieldErrors } from "@auth/passwordPolicy.js";
import { PasswordField } from "@ui/forms/PasswordField.jsx";

import { AuthCardLayout } from "./AuthCardLayout.jsx";
import { PasswordRules } from "./PasswordRules.jsx";
import { TextLink } from "@ui/display/TextLink.jsx";

/**
 * Uso de un enlace de restablecimiento (docs/ux-ui.md L2). Ruta publica
 * `/restablecer?token=…`.
 *
 * Administracion emite el enlace (no hay autoservicio por correo); la persona
 * lo abre y define una contraseña nueva. Al usarlo se cierran todas sus
 * sesiones abiertas.
 */
export function PasswordResetPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState(null);
  const [localError, setLocalError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);
    setLocalError("");
    if (password !== confirm) {
      setLocalError("La contraseña y su confirmación no coinciden.");
      return;
    }
    setSubmitting(true);
    try {
      await authService.consumePasswordReset({ token, password });
      setDone(true);
    } catch (resetError) {
      setError(resetError);
    } finally {
      setSubmitting(false);
    }
  };

  const passwordErrors = fieldErrors(error, "password");
  const generalError =
    error && passwordErrors.length === 0 ? error.message : "";
  const footer = <TextLink to="/login">Volver a iniciar sesión</TextLink>;

  if (!token) {
    return (
      <AuthCardLayout footer={footer}>
        <Stack gap={2}>
          <Typography component="h1" fontWeight={600} variant="h6">
            Restablecer contraseña
          </Typography>
          <Alert severity="warning" variant="outlined">
            El enlace está incompleto. Ábralo tal como se lo entregó
            administración o pida uno nuevo.
          </Alert>
        </Stack>
      </AuthCardLayout>
    );
  }

  if (done) {
    return (
      <AuthCardLayout>
        <Stack gap={2}>
          <Typography component="h1" fontWeight={600} variant="h6">
            Contraseña restablecida
          </Typography>
          <Alert severity="success" variant="outlined">
            Su contraseña nueva quedó guardada y se cerraron sus sesiones
            abiertas. Inicie sesión con ella.
          </Alert>
          <Button component={RouterLink} to="/login" variant="contained">
            Iniciar sesión
          </Button>
        </Stack>
      </AuthCardLayout>
    );
  }

  return (
    <AuthCardLayout footer={footer}>
      <Box component="form" noValidate onSubmit={handleSubmit}>
        <Stack gap={2}>
          <Typography component="h1" fontWeight={600} variant="h6">
            Restablecer contraseña
          </Typography>
          <Typography color="text.secondary" variant="body2">
            Defina una contraseña nueva. El enlace es de un solo uso y vence a
            los 30 minutos de emitido.
          </Typography>

          {localError || generalError ? (
            <Alert role="alert" severity="error" variant="outlined">
              {localError || generalError}
            </Alert>
          ) : null}

          <PasswordField
            autoComplete="new-password"
            disabled={submitting}
            errors={passwordErrors}
            label="Contraseña nueva"
            name="password"
            onChange={(event) => setPassword(event.target.value)}
            required
            value={password}
          />
          <PasswordField
            autoComplete="new-password"
            disabled={submitting}
            label="Confirmar contraseña"
            name="password_confirm"
            onChange={(event) => setConfirm(event.target.value)}
            required
            value={confirm}
          />
          <PasswordRules />

          <Button
            disabled={submitting || !password}
            startIcon={submitting ? <CircularProgress size={16} /> : undefined}
            type="submit"
            variant="contained"
          >
            {submitting ? "Guardando…" : "Guardar contraseña nueva"}
          </Button>
        </Stack>
      </Box>
    </AuthCardLayout>
  );
}
