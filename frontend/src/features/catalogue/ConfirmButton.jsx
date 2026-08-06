import { useState } from "react";

/**
 * Boton de dos pasos para las bajas.
 *
 * La confirmacion vive en la fila en vez de en `window.confirm`: se puede leer
 * con lector de pantalla, se prueba sin dialogos del navegador y deja claro
 * sobre que registro se esta actuando.
 */
export function ConfirmButton({ label, question, confirmLabel, onConfirm }) {
  const [asking, setAsking] = useState(false);
  const [busy, setBusy] = useState(false);

  if (!asking) {
    return (
      <button
        className="button secondary button-small"
        onClick={() => setAsking(true)}
        type="button"
      >
        {label}
      </button>
    );
  }

  const handleConfirm = async () => {
    setBusy(true);
    try {
      await onConfirm();
    } finally {
      setBusy(false);
      setAsking(false);
    }
  };

  return (
    <span className="confirm-inline">
      <span className="muted">{question}</span>
      <button
        className="button button-small button-danger"
        disabled={busy}
        onClick={handleConfirm}
        type="button"
      >
        {busy ? "Procesando..." : confirmLabel}
      </button>
      <button
        className="button secondary button-small"
        disabled={busy}
        onClick={() => setAsking(false)}
        type="button"
      >
        Cancelar
      </button>
    </span>
  );
}
