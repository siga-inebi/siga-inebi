import { useEffect, useRef } from "react";
import Alert from "@mui/material/Alert";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { RecordForm } from "./RecordForm.jsx";
import { studentsService } from "./studentsService.js";
import { fullName } from "./studentPresentation.js";

export function StudentDeactivationForm({
  student,
  onCancel,
  onBusy,
  onCompleted,
}) {
  const heading = useRef(null);
  useEffect(() => {
    heading.current?.focus();
  }, []);
  return (
    <Stack gap={2}>
      <Typography component="h2" variant="h6" ref={heading} tabIndex={-1}>
        Desactivar estudiante: {fullName(student)}
      </Typography>
      <Alert severity="warning">
        El perfil quedará inactivo. Su persona, vínculos, matrículas y registros
        se conservarán. El retiro académico se gestiona en Matrículas.
      </Alert>
      <RecordForm
        title="Desactivar estudiante"
        fields={[]}
        onCancel={onCancel}
        onBusy={onBusy}
        submitLabel="Confirmar desactivación"
        onSubmit={async () => {
          await studentsService.deactivate(student.id);
          onCompleted();
        }}
      />
    </Stack>
  );
}
