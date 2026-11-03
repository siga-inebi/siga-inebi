import { useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { copyToClipboard, printInstructions } from "@shared/utils/print.js";

/**
 * Entrega de un secreto que se muestra UNA sola vez: el codigo de activacion
 * de una cuenta (U1, U2, D8) o el enlace de restablecimiento (U3).
 *
 * Antes se mostraba un token crudo que nadie sabia usar. Ahora va con su
 * vencimiento, las instrucciones para la persona y botones Copiar e Imprimir.
 *
 * @param {object} props
 * @param {boolean} props.open
 * @param {string} props.title
 * @param {string} props.secretLabel   "Código de activación" / "Enlace de restablecimiento".
 * @param {string} props.secret
 * @param {Array<{label: string, value: string}>} props.details  Usuario, vencimiento, etc.
 * @param {string} props.instructions  Que debe hacer la persona con el secreto.
 * @param {Function} props.onClose
 */
export function SecretHandoverDialog({
  details = [],
  instructions,
  onClose,
  open,
  secret,
  secretLabel,
  title,
}) {
  const [feedback, setFeedback] = useState("");

  const copy = async () => {
    const copied = await copyToClipboard(secret);
    setFeedback(
      copied
        ? "Copiado al portapapeles."
        : "El navegador no permitió copiar; selecciónelo y cópielo a mano."
    );
  };

  const print = () => {
    const printed = printInstructions(title, [
      ...details,
      { label: secretLabel, value: secret },
      { value: instructions },
    ]);
    if (!printed) {
      setFeedback("El navegador bloqueó la ventana de impresión.");
    }
  };

  const close = () => {
    setFeedback("");
    onClose();
  };

  return (
    <Dialog fullWidth maxWidth="sm" onClose={close} open={open}>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Stack gap={2}>
          <Alert severity="warning" variant="outlined">
            Se muestra una sola vez. Entréguelo solo a la persona titular de la
            cuenta.
          </Alert>
          <Box component="dl" sx={{ m: 0 }}>
            {details.map((detail) => (
              <Stack direction="row" gap={1} key={detail.label}>
                <Typography
                  color="text.secondary"
                  component="dt"
                  variant="body2"
                >
                  {detail.label}:
                </Typography>
                <Typography component="dd" sx={{ m: 0 }} variant="body2">
                  {detail.value}
                </Typography>
              </Stack>
            ))}
          </Box>
          <Box>
            <Typography color="text.secondary" variant="caption">
              {secretLabel}
            </Typography>
            <Typography
              aria-label={secretLabel}
              sx={{
                fontFamily: "monospace",
                fontSize: "1.125rem",
                overflowWrap: "anywhere",
                p: 1.5,
                borderRadius: 1,
                bgcolor: "action.hover",
              }}
            >
              {secret}
            </Typography>
          </Box>
          <Typography variant="body2">{instructions}</Typography>
          {feedback ? (
            <Typography color="text.secondary" role="status" variant="body2">
              {feedback}
            </Typography>
          ) : null}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2.5, gap: 1 }}>
        <Button onClick={copy} variant="outlined">
          Copiar
        </Button>
        <Button onClick={print} variant="outlined">
          Imprimir instrucciones
        </Button>
        <Button onClick={close} variant="contained">
          Listo
        </Button>
      </DialogActions>
    </Dialog>
  );
}
