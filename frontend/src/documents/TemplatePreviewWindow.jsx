import { useEffect, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";

import { documentsService } from "@documents/documentsService.js";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

/** Preview is server-rendered and deliberately never writes a template or document record. */
export function TemplatePreviewWindow({ onClose, template }) {
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    documentsService
      .previewTemplate(template.public_id, {
        "student.full_name": "Estudiante de ejemplo",
        "institution.name": template.header?.institution_name ?? "Institución",
        "institution.short_name": template.header?.institution_short_name ?? "",
      })
      .then((result) => {
        if (active) setPreview(result);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      });
    return () => {
      active = false;
    };
  }, [template]);

  return (
    <FloatingWindow
      description="Vista previa con datos de muestra. No guarda cambios ni emite un documento oficial."
      footer={
        <Button onClick={onClose} variant="text">
          Cerrar
        </Button>
      }
      onClose={onClose}
      open
      title={`Vista previa: ${template.name}`}
      width={WINDOW_WIDTH.wide}
    >
      <Stack gap={2}>
        {error ? <Alert severity="error">{error}</Alert> : null}
        {!preview && !error ? (
          <CircularProgress aria-label="Generando vista previa" size={28} />
        ) : null}
        {preview ? (
          <>
            <Alert severity="info">
              Se sustituyeron {preview.marker_count} marcador(es) autorizados
              con datos de muestra.
            </Alert>
            <TextField
              aria-label="Contenido de vista previa"
              fullWidth
              minRows={10}
              multiline
              value={preview.content}
              slotProps={{ input: { readOnly: true } }}
            />
          </>
        ) : null}
      </Stack>
    </FloatingWindow>
  );
}
