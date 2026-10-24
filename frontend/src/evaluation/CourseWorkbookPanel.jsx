import { useRef, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import FileUploadOutlinedIcon from "@mui/icons-material/FileUploadOutlined";

import { evaluationService } from "@evaluation/evaluationService.js";
import { downloadResponseFile } from "@shared/utils/download.js";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";

const ERROR_COLUMNS = [
  {
    key: "row",
    label: "Fila",
    align: "right",
    render: (error) => error.row ?? "—",
  },
  {
    key: "student_code",
    label: "Código",
    render: (error) => error.student_code ?? "—",
  },
  { key: "unit", label: "Unidad", render: (error) => error.unit ?? "—" },
  { key: "message", label: "Problema", render: (error) => error.message },
];

function successMessage({ created, updated, unchanged }) {
  const written = created + updated;
  if (written === 0) {
    return unchanged > 0
      ? "El archivo no trae notas nuevas ni cambios: todas coinciden con las registradas."
      : "El archivo no trae notas para registrar.";
  }
  const parts = [`${created} nuevas`, `${updated} corregidas`];
  const same = unchanged > 0 ? ` ${unchanged} ya estaban iguales.` : "";
  return `Se registraron ${written} notas (${parts.join(", ")}).${same}`;
}

/**
 * Carga por Excel de un curso: descarga la plantilla con todas las unidades
 * del ciclo y la vuelve a importar. El backend identifica a cada estudiante
 * por su código, valida todo el archivo y lo guarda todo o nada; aquí solo se
 * muestra el resultado o, fila por fila, qué corregir.
 */
export function CourseWorkbookPanel({
  canWrite,
  cycleId,
  sectionId,
  subjectId,
}) {
  const fileInput = useRef(null);
  const [downloading, setDownloading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [rowErrors, setRowErrors] = useState([]);

  const reset = () => {
    setNotice("");
    setError("");
    setRowErrors([]);
  };

  const download = async () => {
    reset();
    setDownloading(true);
    try {
      const file = await evaluationService.downloadCourseWorkbook(
        cycleId,
        sectionId,
        subjectId
      );
      downloadResponseFile(file, "notas.xlsx");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setDownloading(false);
    }
  };

  const upload = async (event) => {
    const file = event.target.files?.[0];
    // Permite volver a elegir el mismo archivo después de corregirlo.
    event.target.value = "";
    if (!file) return;
    reset();
    setImporting(true);
    try {
      const result = await evaluationService.importCourseWorkbook(
        cycleId,
        sectionId,
        subjectId,
        file
      );
      setNotice(successMessage(result));
    } catch (requestError) {
      const errors = requestError.payload?.errors;
      if (Array.isArray(errors) && errors.length > 0) {
        setRowErrors(errors);
        setError(
          `No se registró ninguna nota: el archivo tiene ${errors.length} ${
            errors.length === 1 ? "problema" : "problemas"
          }. Corríjalos y vuelva a importarlo.`
        );
      } else {
        setError(requestError.message);
      }
    } finally {
      setImporting(false);
    }
  };

  return (
    <SectionCard
      subtitle="Descargue la plantilla del curso con todas las unidades, escriba las notas y vuelva a subirla. Cada estudiante se identifica por su código, no por su nombre."
      title="Carga por Excel"
    >
      <Stack gap={2} sx={{ p: { xs: 1.5, md: 2 } }}>
        <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
          <Button
            disabled={downloading || importing}
            onClick={download}
            startIcon={<FileDownloadOutlinedIcon fontSize="small" />}
            variant="outlined"
          >
            {downloading ? "Generando plantilla…" : "Descargar plantilla"}
          </Button>
          {canWrite ? (
            <>
              <Button
                disabled={downloading || importing}
                onClick={() => fileInput.current?.click()}
                startIcon={<FileUploadOutlinedIcon fontSize="small" />}
                variant="contained"
              >
                {importing ? "Importando…" : "Importar Excel"}
              </Button>
              <input
                accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                aria-label="Archivo de notas"
                hidden
                onChange={upload}
                ref={fileInput}
                type="file"
              />
            </>
          ) : null}
        </Stack>
        {!canWrite ? (
          <Typography color="text.secondary" variant="body2">
            Su cuenta puede descargar la plantilla, pero no importar notas.
          </Typography>
        ) : null}

        {notice ? (
          <Alert role="status" severity="success">
            {notice}
          </Alert>
        ) : null}
        {error ? (
          <Alert role="alert" severity="error">
            {error}
          </Alert>
        ) : null}
        {rowErrors.length > 0 ? (
          <SectionTableArea>
            <DataTable
              columns={ERROR_COLUMNS}
              getRowKey={(item) =>
                `${item.row}-${item.student_code}-${item.unit}-${item.message}`
              }
              rows={rowErrors}
            />
          </SectionTableArea>
        ) : null}
      </Stack>
    </SectionCard>
  );
}
