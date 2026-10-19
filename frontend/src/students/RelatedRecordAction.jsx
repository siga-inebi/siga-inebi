import { useEffect, useRef } from "react";

import Alert from "@mui/material/Alert";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { studentsService } from "./studentsService.js";
import { RecordForm } from "./RecordForm.jsx";

export function RelatedRecordAction({
  selection,
  config,
  onCancel,
  onSaved,
  onBusy,
}) {
  const heading = useRef(null);
  useEffect(() => {
    heading.current?.focus();
  }, []);
  const { row, kind } = selection;
  const editing = kind === "edit";
  const title = `${editing ? "Editar" : "Desactivar"} ${config.singular}`;
  const values = Object.fromEntries(
    config.fields.map(({ name }) => [name, row[name] ?? ""])
  );
  return (
    <Stack gap={2}>
      <Typography component="h2" variant="h6" tabIndex={-1} ref={heading}>
        {title}
        {row.name ? `: ${row.name}` : ""}
      </Typography>
      {!editing ? (
        <>
          <Alert severity="warning">
            El registro dejará de aparecer en la consulta habitual. Su contenido
            e historial se conservarán y podrán consultarse con “Mostrar
            desactivados”.
          </Alert>
          <Typography
            sx={{
              whiteSpace: "pre-wrap",
              overflowWrap: "anywhere",
              maxHeight: 200,
              overflow: "auto",
            }}
          >
            {config.fields
              .map(({ name }) => values[name])
              .filter(Boolean)
              .join(" · ")}
          </Typography>
        </>
      ) : (
        <Typography color="text.secondary">
          La corrección conserva el estudiante y los datos originales de
          registro.
        </Typography>
      )}
      <RecordForm
        title={title}
        fields={editing ? config.fields : []}
        initialValues={values}
        onBusy={onBusy}
        onCancel={onCancel}
        submitLabel={editing ? "Guardar cambios" : "Confirmar desactivación"}
        onSubmit={async (data) => {
          if (editing) {
            const payload = Object.fromEntries(
              config.fields.map(({ name }) => [name, data[name]])
            );
            await studentsService[config.update](row.public_id, payload);
          } else await studentsService[config.deactivate](row.public_id);
          onSaved(kind);
        }}
      />
    </Stack>
  );
}
