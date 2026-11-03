import { useEffect, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
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
        "student.code": "EST-DEMO-0001",
        "institution.name":
          template.header?.institution_name || "Institución de ejemplo",
        "institution.short_name":
          template.header?.institution_short_name || "DEMO",
        "academic.cycle_name": "Ciclo de ejemplo 2026",
        "academic.section_name": "A",
        "enrolment.effective_on": "2026-01-15",
        "document.issue_date": "2026-10-17",
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
            {preview.pdf_base64 ? (
              <Box
                aria-label="Documento PDF de vista previa"
                component="iframe"
                src={`data:${preview.content_type};base64,${preview.pdf_base64}`}
                sx={{ border: 0, minHeight: 620, width: "100%" }}
                title={`Vista previa PDF de ${template.name}`}
              />
            ) : (
              <TextField
                aria-label="Contenido de vista previa"
                fullWidth
                minRows={10}
                multiline
                value={preview.content}
                slotProps={{ input: { readOnly: true } }}
              />
            )}
          </>
        ) : null}
      </Stack>
    </FloatingWindow>
  );
}
