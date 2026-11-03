import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";

import { formatCountdown } from "./sessionTimer.js";

/**
 * Aviso de sesion por vencer (docs/ux-ui.md L4): aparece 2 minutos antes del
 * cierre por inactividad para que nadie pierda el formulario que estaba
 * llenando.
 */
export function SessionTimeoutDialog({
  busy,
  onLogout,
  onStay,
  open,
  remainingMs,
}) {
  return (
    <Dialog aria-describedby="session-timeout-text" open={open}>
      <DialogTitle>Su sesión está por cerrarse</DialogTitle>
      <DialogContent>
        <DialogContentText id="session-timeout-text" variant="body2">
          Por inactividad, su sesión se cerrará en{" "}
          <strong>{formatCountdown(remainingMs)}</strong>. Lo que no haya
          guardado se perderá.
        </DialogContentText>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2.5, gap: 1 }}>
        <Button disabled={busy} onClick={onLogout} variant="text">
          Cerrar sesión
        </Button>
        <Button
          disabled={busy}
          onClick={onStay}
          startIcon={busy ? <CircularProgress size={16} /> : undefined}
          variant="contained"
        >
          Seguir conectado
        </Button>
      </DialogActions>
    </Dialog>
  );
}
