import { useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { authService } from "@auth/authService.js";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

/**
 * Ventana modal para que el usuario autenticado actualice su contraseña personal (RF-AUT-006).
 *
 * @param {object}   props
 * @param {boolean}  props.open
 * @param {Function} props.onClose
 * @param {Function} [props.onSuccess]
 */
export function ChangePasswordWindow({ onClose, onSuccess, open }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newPasswordConfirm, setNewPasswordConfirm] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const resetForm = () => {
    setCurrentPassword("");
    setNewPassword("");
    setNewPasswordConfirm("");
    setError("");
    setSuccess(false);
    setSubmitting(false);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    if (!currentPassword || !newPassword || !newPasswordConfirm) {
      setError("Todos los campos son obligatorios.");
      return;
    }

    if (newPassword !== newPasswordConfirm) {
      setError("La nueva contraseña y su confirmación no coinciden.");
      return;
    }

    setSubmitting(true);
    try {
      await authService.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      });
      setSuccess(true);
      if (onSuccess) {
        onSuccess();
      }
      setTimeout(() => {
        handleClose();
      }, 1200);
    } catch (err) {
      setError(
        err?.message ||
          "Ocurrió un error al intentar cambiar la contraseña. Verifique los datos."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <FloatingWindow
      description="Por seguridad, ingresar su contraseña actual para establecer una nueva clave."
      onClose={handleClose}
      open={open}
      title="Cambiar contraseña"
      width={WINDOW_WIDTH.narrow || "480px"}
    >
      <Box component="form" noValidate onSubmit={handleSubmit}>
        <Stack spacing={2.5}>
          {error ? (
            <Alert severity="error" variant="outlined">
              {error}
            </Alert>
          ) : null}

          {success ? (
            <Alert severity="success" variant="outlined">
              Contraseña actualizada exitosamente.
            </Alert>
          ) : null}

          <FormTextField
            autoComplete="current-password"
            disabled={submitting || success}
            label="Contraseña actual"
            name="currentPassword"
            onChange={(event) => setCurrentPassword(event.target.value)}
            required
            type="password"
            value={currentPassword}
          />

          <FormTextField
            autoComplete="new-password"
            disabled={submitting || success}
            helperText="Debe contener al menos 8 caracteres."
            label="Nueva contraseña"
            name="newPassword"
            onChange={(event) => setNewPassword(event.target.value)}
            required
            type="password"
            value={newPassword}
          />

          <FormTextField
            autoComplete="new-password"
            disabled={submitting || success}
            label="Confirmar nueva contraseña"
            name="newPasswordConfirm"
            onChange={(event) => setNewPasswordConfirm(event.target.value)}
            required
            type="password"
            value={newPasswordConfirm}
          />

          <Typography color="text.secondary" variant="caption">
            Al cambiar su contraseña, se cerrarán las sesiones abiertas en otros
            dispositivos.
          </Typography>

          <Stack
            direction="row"
            justifyContent="flex-end"
            spacing={1.5}
            sx={{ pt: 1 }}
          >
            <Button
              color="inherit"
              disabled={submitting}
              onClick={handleClose}
              variant="outlined"
            >
              Cancelar
            </Button>
            <Button
              disabled={submitting || success}
              startIcon={
                submitting ? (
                  <CircularProgress color="inherit" size={16} />
                ) : null
              }
              type="submit"
              variant="contained"
            >
              {submitting ? "Actualizando..." : "Actualizar contraseña"}
            </Button>
          </Stack>
        </Stack>
      </Box>
    </FloatingWindow>
  );
}
