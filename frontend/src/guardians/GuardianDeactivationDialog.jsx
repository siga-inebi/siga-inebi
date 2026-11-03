import { useRef, useState } from "react";

import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";
import { guardiansService } from "./guardiansService.js";

export function GuardianDeactivationDialog({
  guardian,
  onCancel,
  onCompleted,
}) {
  const pending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const confirm = async () => {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      await guardiansService.deactivate(guardian.id);
    } catch (failure) {
      setError(failure.message);
      pending.current = false;
      setBusy(false);
      return;
    }
    // El DELETE confirmado y la posterior recarga son operaciones distintas.
    // Un fallo de lectura no debe ofrecer repetir una escritura ya realizada.
    onCompleted();
  };
  return (
    <ConfirmDialog
      open
      title="Desactivar encargado"
      message={`¿Desea desactivar a ${guardian.person.first_name} ${guardian.person.last_name}? El perfil dejará de aparecer en el listado activo. Se conservarán su persona, cuenta e historial de vínculos. Dejará de obtener acceso a estudiantes por esos vínculos. Su cuenta y los permisos obtenidos por otros roles seguirán vigentes.`}
      confirmText="Desactivar encargado"
      confirmColor="error"
      busy={busy}
      errorText={error}
      onConfirm={confirm}
      onClose={() => {
        if (!pending.current) onCancel();
      }}
    />
  );
}
