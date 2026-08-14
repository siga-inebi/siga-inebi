import { useState } from "react";

import Button from "@mui/material/Button";

import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";

/**
 * Accion destructiva o irreversible en dos pasos.
 *
 * Usa un dialogo del sistema en vez de `window.confirm`: el nativo no se puede
 * estilar, no dice sobre que registro actua y bloquea el hilo del navegador.
 *
 * @param {object}   props
 * @param {string}   props.label        Texto del boton disparador.
 * @param {string}   props.title        Titulo del dialogo.
 * @param {string}   props.question     Pregunta de confirmacion.
 * @param {string}   props.confirmLabel Texto del boton que confirma.
 * @param {Function} props.onConfirm    Puede ser asincrono.
 * @param {string}  [props.color="error"]
 */
export function ConfirmActionButton({
  color = "error",
  confirmLabel,
  label,
  onConfirm,
  question,
  size = "small",
  title,
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const handleConfirm = async () => {
    setBusy(true);
    setError("");
    try {
      await onConfirm();
      setOpen(false);
    } catch (actionError) {
      // El dialogo queda abierto con el motivo: cerrarlo dejaria al usuario sin
      // saber si la accion procedio.
      setError(actionError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Button
        color={color}
        onClick={() => setOpen(true)}
        size={size}
        variant="text"
      >
        {label}
      </Button>
      <ConfirmDialog
        busy={busy}
        confirmColor={color}
        confirmText={busy ? `${confirmLabel}…` : confirmLabel}
        errorText={error || undefined}
        message={question}
        onClose={() => {
          setOpen(false);
          setError("");
        }}
        onConfirm={handleConfirm}
        open={open}
        title={title ?? label}
      />
    </>
  );
}
