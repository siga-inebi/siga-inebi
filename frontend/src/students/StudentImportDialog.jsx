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
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import UploadFileOutlinedIcon from "@mui/icons-material/UploadFileOutlined";

import { studentsService } from "@students/studentsService.js";
import { useInvalidate } from "@shared/api/invalidation.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";

const STEPS = ["Archivo", "Vista previa", "Resultado"];

const ROW_STATUS_LABEL = { ready: "Lista", error: "Con errores" };
const ROW_STATUS_VARIANT = { ready: "success", error: "danger" };

const PREVIEW_COLUMNS = [
  { key: "linea", label: "Línea", render: (row) => row.line },
  {
    key: "nombre",
    label: "Nombre",
    render: (row) =>
      [row.data?.nombres, row.data?.apellidos].filter(Boolean).join(" ") || "—",
  },
  { key: "cui", label: "CUI", render: (row) => row.data?.cui || "—" },
  {
    key: "codigo",
    label: "Código",
    render: (row) => row.data?.codigo_estudiante || "Se asigna solo",
  },
  {
    key: "estado",
    label: "Estado",
    render: (row) => (
      <StatusChip
        label={ROW_STATUS_LABEL[row.status] ?? row.status}
        variant={ROW_STATUS_VARIANT[row.status] ?? "neutral"}
      />
    ),
  },
  {
    key: "errores",
    label: "Errores",
    render: (row) =>
      row.errors?.length ? (
        <Box component="ul" sx={{ m: 0, pl: 2 }}>
          {row.errors.map((message, index) => (
            <Typography component="li" key={index} variant="body2">
              {message}
            </Typography>
          ))}
        </Box>
      ) : (
        "—"
      ),
  },
];

/**
 * Indicador de pasos. No es el `Stepper` de MUI a propósito: todo componente
 * de MUI viaja en el chunk inicial (`vite.config.js`), y el Stepper solo
 * rompía el presupuesto de carga inicial (`check-build-budget.mjs`).
 */
function ImportSteps({ active }) {
  return (
    <Box
      aria-label="Pasos de la importación"
      component="ol"
      sx={{
        display: "flex",
        flexWrap: "wrap",
        gap: { xs: 1, sm: 3 },
        listStyle: "none",
        m: 0,
        p: 0,
      }}
    >
      {STEPS.map((label, index) => (
        <Box
          aria-current={index === active ? "step" : undefined}
          component="li"
          key={label}
          sx={{
            alignItems: "center",
            color: index <= active ? "text.primary" : "text.secondary",
            display: "flex",
            fontWeight: index === active ? 700 : 400,
            gap: 1,
          }}
        >
          <Box
            component="span"
            sx={{
              alignItems: "center",
              bgcolor: index <= active ? "primary.main" : "action.disabled",
              borderRadius: "50%",
              color: "primary.contrastText",
              display: "inline-flex",
              fontSize: 12,
              height: 24,
              justifyContent: "center",
              width: 24,
            }}
          >
            {index + 1}
          </Box>
          {label}
        </Box>
      ))}
    </Box>
  );
}

/** Un 422 de la confirmación trae las filas con el mismo sobre de la vista previa. */
function rejectedPreview(error) {
  const body = error?.payload;
  if (body?.rows) return body;
  if (body?.error?.rows) return body.error;
  return null;
}

/**
 * Importación CSV de estudiantes, todo o nada: archivo → vista previa →
 * resultado.
 *
 * Las reglas de cada fila las aplica el backend (las mismas del alta); aquí
 * solo se muestran. "Confirmar inserción" se habilita únicamente sin errores,
 * y si la confirmación falla (el archivo cambió, o una fila dejó de ser
 * válida) el diálogo queda abierto con los motivos: no se insertó nada.
 *
 * @param {object}   props
 * @param {boolean}  props.open
 * @param {Function} props.onClose
 * @param {Function} props.onDownloadTemplate
 */
export function StudentImportDialog({ onClose, onDownloadTemplate, open }) {
  const invalidate = useInvalidate();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const step = result ? 2 : preview ? 1 : 0;
  const errors = preview?.summary?.errors ?? 0;

  const validate = async () => {
    setBusy(true);
    setError("");
    try {
      setPreview(await studentsService.previewImport(file));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const confirm = async () => {
    setBusy(true);
    setError("");
    try {
      setResult(await studentsService.confirmImport(file, preview.file_sha256));
      invalidate(queryKeys.students.all);
    } catch (requestError) {
      const rejected =
        requestError.status === 422 ? rejectedPreview(requestError) : null;
      if (rejected) setPreview(rejected);
      setError(
        requestError.status === 409
          ? "El archivo cambió desde la vista previa. Vuelva a validarlo antes de confirmar."
          : rejected
            ? "No se insertó ningún estudiante: hay filas con errores. Corrija el archivo y vuelva a validarlo."
            : requestError.message
      );
    } finally {
      setBusy(false);
    }
  };

  const restart = () => {
    setPreview(null);
    setError("");
  };

  return (
    <Dialog
      fullWidth
      maxWidth="lg"
      onClose={busy ? undefined : onClose}
      open={open}
    >
      <DialogTitle>Importar estudiantes desde CSV</DialogTitle>
      <DialogContent>
        <Stack gap={2}>
          <ImportSteps active={step} />

          {step === 0 ? (
            <Stack gap={1.5}>
              <Typography variant="body2">
                Use la plantilla: una fila por estudiante. Si una sola fila
                tiene errores no se inserta ninguna, y la vista previa dice el
                motivo de cada una.
              </Typography>
              <Stack direction="row" flexWrap="wrap" gap={1}>
                <Button
                  component="label"
                  disabled={busy}
                  startIcon={<UploadFileOutlinedIcon fontSize="small" />}
                  variant="outlined"
                >
                  Elegir archivo CSV
                  <input
                    accept=".csv,text/csv"
                    aria-label="Archivo CSV"
                    hidden
                    onChange={(event) => {
                      setFile(event.target.files?.[0] ?? null);
                      setError("");
                    }}
                    type="file"
                  />
                </Button>
                <Button
                  disabled={busy}
                  onClick={onDownloadTemplate}
                  startIcon={<FileDownloadOutlinedIcon fontSize="small" />}
                  variant="text"
                >
                  Descargar plantilla
                </Button>
              </Stack>
              <Typography color="text.secondary" variant="body2">
                {file ? `Archivo: ${file.name}` : "Ningún archivo elegido."}
              </Typography>
            </Stack>
          ) : null}

          {step === 1 ? (
            <>
              <Typography role="status" variant="body2">
                {preview.summary.total} filas: {preview.summary.ready} listas y{" "}
                {errors} con errores.
              </Typography>
              <DataTable
                columns={PREVIEW_COLUMNS}
                getRowKey={(row) => row.line}
                rows={preview.rows}
              />
            </>
          ) : null}

          {step === 2 ? (
            <Alert severity="success">
              Se crearon {result.created} estudiantes.
            </Alert>
          ) : null}

          {error ? (
            <Alert role="alert" severity="error">
              {error}
            </Alert>
          ) : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button disabled={busy} onClick={onClose}>
          {step === 2 ? "Cerrar" : "Cancelar"}
        </Button>
        {step === 0 ? (
          <Button
            disabled={busy || !file}
            onClick={validate}
            variant="contained"
          >
            Validar archivo
          </Button>
        ) : null}
        {step === 1 ? (
          <>
            <Button disabled={busy} onClick={restart}>
              Elegir otro archivo
            </Button>
            <Button disabled={busy} onClick={validate}>
              Volver a validar
            </Button>
            <Button
              disabled={busy || errors > 0}
              onClick={confirm}
              variant="contained"
            >
              Confirmar inserción
            </Button>
          </>
        ) : null}
      </DialogActions>
    </Dialog>
  );
}
