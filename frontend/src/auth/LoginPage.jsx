import { useState } from "react";
import {
  Link as RouterLink,
  Navigate,
  useLocation,
  useNavigate,
} from "react-router-dom";

import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { PasswordField } from "@ui/forms/PasswordField.jsx";
import { useAuth } from "@auth/useAuth.js";

import { AuthCardLayout } from "./AuthCardLayout.jsx";
import { SESSION_NOTICE } from "./sessionTimer.js";
import { TextLink } from "@ui/display/TextLink.jsx";

/** Codigo con que el backend marca un bloqueo temporal por intentos fallidos (L5). */
const LOCKED_CODE = "account_locked";

function isLockedError(error) {
  const code = error?.payload?.error?.detail?.code;
  return Array.isArray(code)
    ? code.includes(LOCKED_CODE)
    : code === LOCKED_CODE;
}

/** Destino al entrar: la pagina que se estaba usando, con su busqueda (L4). */
function returnPath(location) {
  const from = location.state?.from;
  if (!from?.pathname) return "/app";
  return `${from.pathname}${from.search ?? ""}`;
}

export function LoginPage() {
  const { isAuthenticated, login, sessionNotice } = useAuth();
  const location = useLocation();
  const [username, setUsername] = useState(location.state?.username ?? "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const navigate = useNavigate();

  if (isAuthenticated) {
    return <Navigate replace to={returnPath(location)} />;
  }

  // Booleano calculado en render, no estado: un `canSubmit` en useState se
  // desincroniza del formulario en el primer camino que se olvide de setearlo.
  const canSubmit = username.trim() !== "" && password !== "" && !submitting;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError(null);
    try {
      await login({ username, password });
      navigate(returnPath(location), { replace: true });
    } catch (loginError) {
      setError(loginError);
    } finally {
      setSubmitting(false);
    }
  };

  const locked = isLockedError(error);

  return (
    <AuthCardLayout>
      <Box component="form" noValidate onSubmit={handleSubmit}>
        <Stack gap={2}>
          <Typography component="h1" fontWeight={600} variant="h6">
            Iniciar sesión
          </Typography>

          {sessionNotice === SESSION_NOTICE.EXPIRED && !error ? (
            <Alert severity="info" variant="outlined">
              Su sesión se cerró por inactividad. Ingrese de nuevo para
              continuar donde estaba.
            </Alert>
          ) : null}

          {error && locked ? (
            <Alert role="alert" severity="warning" variant="outlined">
              <AlertTitle>Cuenta bloqueada temporalmente</AlertTitle>
              {error.message} Si necesita entrar antes, administración puede
              desbloquear su cuenta.
            </Alert>
          ) : null}
          {error && !locked ? (
            <Alert role="alert" severity="error" variant="outlined">
              {error.message}
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
          <PasswordField
            autoComplete="current-password"
            disabled={submitting}
            label="Contraseña"
            name="password"
            onChange={(event) => setPassword(event.target.value)}
            value={password}
          />

          {/*
            "Mantener sesion iniciada" no se implementa a proposito: la duracion
            de la sesion la decide el backend por rol y no hay contrato para
            pedir una sesion larga. Un checkbox que no cambia nada promete algo
            que el sistema no cumple.
          */}
          <Button
            disabled={!canSubmit}
            fullWidth
            size="large"
            startIcon={submitting ? <CircularProgress size={16} /> : undefined}
            type="submit"
            variant="contained"
          >
            {submitting ? "Validando acceso…" : "Ingresar"}
          </Button>

          <Stack alignItems="center" gap={0.5}>
            <Button
              aria-expanded={helpOpen}
              onClick={() => setHelpOpen((value) => !value)}
              size="small"
              variant="text"
            >
              ¿Olvidó su contraseña?
            </Button>
            {helpOpen ? (
              <Alert severity="info" sx={{ width: "100%" }} variant="outlined">
                El restablecimiento lo emite administración: no hay envío por
                correo. Pida a administración un enlace de restablecimiento y
                ábralo en este navegador para definir una contraseña nueva.
              </Alert>
            ) : null}
            <TextLink to="/activar">Recibí un código de activación</TextLink>
          </Stack>
        </Stack>
      </Box>
    </AuthCardLayout>
  );
}
