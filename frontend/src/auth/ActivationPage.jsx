import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { authService } from "@auth/authService.js";
import { fieldErrors } from "@auth/passwordPolicy.js";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { PasswordField } from "@ui/forms/PasswordField.jsx";

import { AuthCardLayout } from "./AuthCardLayout.jsx";
import { PasswordRules } from "./PasswordRules.jsx";
import { TextLink } from "@ui/display/TextLink.jsx";

/**
 * Activacion de cuenta (docs/ux-ui.md L1). Ruta publica `/activar`.
 *
 * Administracion crea la cuenta y entrega un codigo de 8 digitos de un solo uso.
 * Aqui la persona lo canjea con su usuario y define su contraseña. Los errores
 * de la contraseña se muestran junto al campo, regla por regla (MC2).
 */
export function ActivationPage() {
  const [values, setValues] = useState({
    username: "",
    activation_code: "",
    password: "",
    password_confirm: "",
  });
  const [error, setError] = useState(null);
  const [localError, setLocalError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [activated, setActivated] = useState(null);

  const set = (name) => (event) =>
    setValues((current) => ({ ...current, [name]: event.target.value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);
    setLocalError("");
    if (!values.username.trim() || !values.activation_code.trim()) {
      setLocalError("Escriba su usuario y el código de activación.");
      return;
    }
    if (values.password !== values.password_confirm) {
      setLocalError("La contraseña y su confirmación no coinciden.");
      return;
    }
    setSubmitting(true);
    try {
      const result = await authService.activate({
        username: values.username.trim(),
        activation_code: values.activation_code.trim(),
        password: values.password,
      });
      setActivated(result);
    } catch (activationError) {
      setError(activationError);
    } finally {
      setSubmitting(false);
    }
  };

  const passwordErrors = fieldErrors(error, "password");
  const generalError =
    error && passwordErrors.length === 0 ? error.message : "";

  if (activated) {
    return (
      <AuthCardLayout>
        <Stack gap={2}>
          <Typography component="h1" fontWeight={600} variant="h6">
            Cuenta activada
          </Typography>
          <Alert severity="success" variant="outlined">
            Su cuenta «{activated.username}» quedó activa. Ya puede iniciar
            sesión con la contraseña que acaba de definir.
          </Alert>
          <Button
            component={RouterLink}
            state={{ username: activated.username }}
            to="/login"
            variant="contained"
          >
            Iniciar sesión
          </Button>
        </Stack>
      </AuthCardLayout>
    );
  }

  return (
    <AuthCardLayout
      footer={<TextLink to="/login">Volver a iniciar sesión</TextLink>}
    >
      <Box component="form" noValidate onSubmit={handleSubmit}>
        <Stack gap={2}>
          <Typography component="h1" fontWeight={600} variant="h6">
            Activar mi cuenta
          </Typography>
          <Typography color="text.secondary" variant="body2">
            Use el usuario y el código de activación que le entregó
            administración. El código es de un solo uso y vence.
          </Typography>

          {localError || generalError ? (
            <Alert role="alert" severity="error" variant="outlined">
              {localError || generalError}
            </Alert>
          ) : null}

          <FormTextField
            autoComplete="username"
            disabled={submitting}
            label="Usuario institucional"
            name="username"
            onChange={set("username")}
            required
            value={values.username}
          />
          <FormTextField
            autoComplete="one-time-code"
            disabled={submitting}
            label="Código de activación"
            name="activation_code"
            onChange={set("activation_code")}
            required
            slotProps={{ htmlInput: { inputMode: "numeric", maxLength: 8 } }}
            value={values.activation_code}
          />
          <PasswordField
            autoComplete="new-password"
            disabled={submitting}
            errors={passwordErrors}
            label="Contraseña nueva"
            name="password"
            onChange={set("password")}
            required
            value={values.password}
          />
          <PasswordField
            autoComplete="new-password"
            disabled={submitting}
            label="Confirmar contraseña"
            name="password_confirm"
            onChange={set("password_confirm")}
            required
            value={values.password_confirm}
          />
          <PasswordRules />

          <Button
            disabled={submitting}
            startIcon={submitting ? <CircularProgress size={16} /> : undefined}
            type="submit"
            variant="contained"
          >
            {submitting ? "Activando…" : "Activar cuenta"}
          </Button>
        </Stack>
      </Box>
    </AuthCardLayout>
  );
}
