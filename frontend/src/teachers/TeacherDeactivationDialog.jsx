import { useRef, useState } from "react";

import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";
import { teachersService } from "./teachersService.js";

export function TeacherDeactivationDialog({ teacher, onCancel, onCompleted }) {
  const pending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const confirm = async () => {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError("");
    try {
      await teachersService.deactivate(teacher.id);
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
      title="Desactivar docente"
      message={`¿Desea desactivar a ${teacher.person.first_name} ${teacher.person.last_name} (${teacher.employee_code})? El perfil dejará de aparecer en el listado activo. Su persona, cuenta, asignaciones y documentos se conservarán. Esta acción no desactiva su cuenta de acceso ni finaliza asignaciones académicas.`}
      confirmText="Desactivar docente"
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
