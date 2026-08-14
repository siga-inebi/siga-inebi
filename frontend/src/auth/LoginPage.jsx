import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { BrandMark } from "@layout/BrandMark.jsx";
import { ColorModeToggle } from "@layout/ColorModeToggle.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";
import { useAuth } from "@auth/useAuth.js";

export function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  if (isAuthenticated) {
    return <Navigate replace to="/app" />;
  }

  // Booleano calculado en render, no estado: un `canSubmit` en useState se
  // desincroniza del formulario en el primer camino que se olvide de setearlo.
  const canSubmit = username.trim() !== "" && password !== "" && !submitting;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError("");
    try {
      await login({ username, password });
      navigate(location.state?.from?.pathname || "/app", { replace: true });
    } catch (loginError) {
      setError(loginError.message);
    } finally {
      setSubmitting(false);
    }
  };

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
      <Box sx={{ width: "100%", maxWidth: 420 }}>
        <Stack alignItems="center" gap={2} sx={{ mb: 3 }}>
          <BrandMark compact size="large" />
          <Box sx={{ textAlign: "center" }}>
            <Typography fontWeight="bold" variant="h5">
              SIGA-INEBI
            </Typography>
            <Typography color="text.secondary" variant="body2">
              Instituto Nacional de Educacion Basica de Salcaja
            </Typography>
          </Box>
        </Stack>

        <SectionCard>
          <Box
            component="form"
            noValidate
            onSubmit={handleSubmit}
            sx={{ p: 3 }}
          >
            <Stack gap={2}>
              <Typography component="h1" fontWeight={600} variant="h6">
                Iniciar sesion
              </Typography>

              {error ? (
                <Alert severity="error" variant="outlined">
                  {error}
                </Alert>
              ) : null}

              <FormTextField
                autoComplete="username"
                disabled={submitting}
                label="Usuario institucional"
                name="username"
                onChange={(event) => setUsername(event.target.value)}
                value={username}
              />
              <FormTextField
                autoComplete="current-password"
                disabled={submitting}
                label="Contrasena"
                name="password"
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                value={password}
              />

              {/*
                El mockup incluye "Mantener sesion iniciada". No se implementa
                todavia a proposito: la duracion de la sesion la decide el
                backend (cookie de sesion de Django) y no hay contrato para
                pedir una sesion larga. Un checkbox que no cambia nada es peor
                que su ausencia, porque promete algo que el sistema no cumple.
              */}
              <Button
                disabled={!canSubmit}
                fullWidth
                size="large"
                startIcon={
                  submitting ? <CircularProgress size={16} /> : undefined
                }
                type="submit"
                variant="contained"
              >
                {submitting ? "Validando acceso…" : "Ingresar"}
              </Button>

              <Typography
                color="text.secondary"
                sx={{ textAlign: "center" }}
                variant="body2"
              >
                Olvido su contrasena? Contacte a administracion.
              </Typography>
            </Stack>
          </Box>
        </SectionCard>

        <Stack alignItems="center" gap={1.5} sx={{ mt: 3 }}>
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
