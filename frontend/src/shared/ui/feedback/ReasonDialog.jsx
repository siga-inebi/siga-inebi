import { useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";

import { FormTextField } from "@ui/forms/FormTextField.jsx";

/**
 * Confirmacion que exige un motivo, para operaciones auditadas (reactivar,
 * desbloquear, retirar un rol...). El motivo queda en la bitacora.
 *
 * @param {object} props
 * @param {boolean} props.open
 * @param {string} props.title
 * @param {React.ReactNode} props.message
 * @param {(reason: string) => Promise<void>} props.onConfirm  Puede rechazar: el error se muestra sin cerrar.
 * @param {Function} props.onClose
 * @param {string} [props.confirmText="Confirmar"]
 * @param {"primary"|"error"|"warning"} [props.confirmColor="primary"]
 */
export function ReasonDialog({
  confirmColor = "primary",
  confirmText = "Confirmar",
  message,
  onClose,
  onConfirm,
  open,
  title,
}) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const close = () => {
    if (busy) return;
    setReason("");
    setError("");
    onClose();
  };

  const confirm = async () => {
    if (!reason.trim()) {
      setError("Escriba el motivo: queda registrado en la bitácora.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await onConfirm(reason.trim());
      setReason("");
    } catch (confirmError) {
      setError(confirmError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog fullWidth maxWidth="sm" onClose={close} open={open}>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }} variant="body2">
          {message}
        </DialogContentText>
        {error ? (
          <Alert role="alert" severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        ) : null}
        <FormTextField
          disabled={busy}
          fullWidth
          label="Motivo"
          minRows={2}
          multiline
          name="reason"
          onChange={(event) => setReason(event.target.value)}
          required
          value={reason}
        />
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2.5, gap: 1 }}>
        <Button disabled={busy} onClick={close} variant="text">
          Cancelar
        </Button>
        <Button
          color={confirmColor}
          disabled={busy}
          onClick={confirm}
          startIcon={busy ? <CircularProgress size={16} /> : undefined}
          variant="contained"
        >
          {confirmText}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
