import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";

/**
 * Confirmacion binaria.
 *
 * Orden de botones fijo: Cancelar (text) a la izquierda, accion (contained) a
 * la derecha. Invertirlo entre pantallas es como se consiguen borrados
 * accidentales por memoria muscular.
 *
 * @param {object}   props
 * @param {boolean}  props.open
 * @param {string}   props.title
 * @param {string}   props.message
 * @param {Function} props.onConfirm
 * @param {Function} props.onClose
 * @param {string}  [props.confirmText="Confirmar"]
 * @param {string}  [props.confirmColor="primary"]
 * @param {boolean} [props.busy]
 * @param {string}  [props.errorText] Motivo de dominio por el que no procede.
 */
export function ConfirmDialog({
  busy = false,
  confirmColor = "primary",
  confirmText = "Confirmar",
  errorText,
  message,
  onClose,
  onConfirm,
  open,
  title,
}) {
  return (
    <Dialog onClose={busy ? undefined : onClose} open={open}>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText variant="body2">{message}</DialogContentText>
        {errorText ? (
          <DialogContentText color="error" sx={{ mt: 2 }} variant="body2">
            {errorText}
          </DialogContentText>
        ) : null}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2.5, gap: 1 }}>
        <Button disabled={busy} onClick={onClose} variant="text">
          Cancelar
        </Button>
        <Button
          color={confirmColor}
          disabled={busy}
          onClick={onConfirm}
          startIcon={busy ? <CircularProgress size={16} /> : undefined}
          variant="contained"
        >
          {confirmText}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
