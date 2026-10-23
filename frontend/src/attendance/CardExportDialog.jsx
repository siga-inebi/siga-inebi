import { useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { attendanceService } from "@attendance/attendanceService.js";
import { CardExportStudentPicker } from "@attendance/CardExportStudentPicker.jsx";

import { downloadResponseFile } from "@shared/utils/download.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";

/** Estado de cada fila de la vista previa de exportación. */
const ROW_STATUS_LABEL = {
  ready: "Listo",
  to_issue: "Se emitirá",
  skipped: "Omitido",
};

const ROW_STATUS_VARIANT = {
  ready: "success",
  to_issue: "warning",
  skipped: "danger",
};

const FORMAT_OPTIONS = [
  { value: "pdf", label: "PDF (un solo archivo con todos los carnés)" },
  { value: "zip", label: "ZIP (una imagen PNG por carné)" },
];
// Solo con un estudiante: el backend rechaza `png` para más de uno.
const PNG_OPTION = { value: "png", label: "PNG (la imagen del carné)" };

const STEP_TITLE = {
  select: "Paso 1 de 3: seleccionar estudiantes",
  format: "Paso 2 de 3: formato",
  preview: "Paso 3 de 3: vista previa",
};

const PREVIEW_COLUMNS = [
  {
    key: "estudiante",
    label: "Estudiante",
    render: (row) => (
      <>
        <Typography variant="body2">{row.full_name}</Typography>
        <Typography color="text.secondary" variant="caption">
          {row.student_code}
        </Typography>
      </>
    ),
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
  { key: "motivo", label: "Motivo", render: (row) => row.reason || "—" },
];

/**
 * Exportación de carnés (RF-CRE-002): seleccionar estudiantes → formato →
 * vista previa → confirmar y descargar.
 *
 * La vista previa no emite nada; dice qué carnés están listos, cuáles se
 * emitirán al confirmar y cuáles se omiten y por qué. Esa decisión es del
 * backend: aquí solo se muestra.
 *
 * La selección (hasta 100, `CARD_EXPORT_LIMIT`; el backend rechaza más) vive
 * aquí: el selector del paso 1 sigue montado, oculto, en los pasos siguientes
 * para que volver conserve filtros y página.
 *
 * @param {object}   props
 * @param {boolean}  props.open
 * @param {Function} props.onClose
 * @param {Function} [props.onExported] Tras descargar el archivo.
 */
export function CardExportDialog({ onClose, onExported, open }) {
  const [studentIds, setStudentIds] = useState([]);
  const [step, setStep] = useState("select");
  const [format, setFormat] = useState("pdf");
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const exportable = preview
    ? preview.summary.ready + preview.summary.to_issue
    : 0;

  const run = async (action) => {
    setBusy(true);
    setError("");
    try {
      await action();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const formatOptions =
    studentIds.length === 1 ? [...FORMAT_OPTIONS, PNG_OPTION] : FORMAT_OPTIONS;

  const goToFormat = () => {
    if (format === "png" && studentIds.length !== 1) setFormat("pdf");
    setPreview(null);
    setError("");
    setStep("format");
  };

  const loadPreview = () =>
    run(async () => {
      setPreview(await attendanceService.previewCardExport(studentIds, format));
      setStep("preview");
    });

  const confirm = () =>
    run(async () => {
      const file = await attendanceService.exportCards(studentIds, format);
      downloadResponseFile(file, `carnes.${format}`);
      setDone(true);
      onExported?.();
    });

  return (
    <Dialog
      fullWidth
      maxWidth="md"
      onClose={busy ? undefined : onClose}
      open={open}
    >
      <DialogTitle>
        Exportar carnés ({studentIds.length})
        <Typography color="text.secondary" component="span" display="block">
          {STEP_TITLE[step]}
        </Typography>
      </DialogTitle>
      <DialogContent>
        <Stack gap={2}>
          <Box sx={{ display: step === "select" ? undefined : "none" }}>
            <CardExportStudentPicker
              onSelectionChange={setStudentIds}
              selectedIds={studentIds}
            />
          </Box>
          {step === "format" ? (
            // Un select y no radios: los componentes de MUI viajan en el chunk
            // inicial (vite.config.js), y este ya está ahí.
            <TextField
              disabled={busy}
              label="Formato del archivo"
              onChange={(event) => setFormat(event.target.value)}
              select
              size="small"
              value={format}
            >
              {formatOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
          ) : null}
          {step === "preview" && preview ? (
            <>
              <Typography role="status" variant="body2">
                {preview.summary.total} seleccionados: {preview.summary.ready}{" "}
                listos, {preview.summary.to_issue} se emitirán al confirmar y{" "}
                {preview.summary.skipped} se omiten.
              </Typography>
              <DataTable
                columns={PREVIEW_COLUMNS}
                getRowKey={(row) => row.student_id}
                rows={preview.rows}
              />
              {exportable === 0 ? (
                <Alert severity="warning">
                  Ningún estudiante seleccionado tiene un carné exportable.
                </Alert>
              ) : null}
            </>
          ) : null}

          {error ? (
            <Alert role="alert" severity="error">
              {error}
            </Alert>
          ) : null}
          {done ? (
            <Alert severity="success">
              Se descargó el archivo con {exportable} carnés.
            </Alert>
          ) : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button disabled={busy} onClick={onClose}>
          {done ? "Cerrar" : "Cancelar"}
        </Button>
        {step === "select" ? (
          <Button
            disabled={!studentIds.length}
            onClick={goToFormat}
            variant="contained"
          >
            Continuar
          </Button>
        ) : step === "format" ? (
          <>
            <Button disabled={busy} onClick={() => setStep("select")}>
              Cambiar selección
            </Button>
            <Button
              disabled={busy || !studentIds.length}
              onClick={loadPreview}
              variant="contained"
            >
              Ver vista previa
            </Button>
          </>
        ) : !done ? (
          <>
            <Button disabled={busy} onClick={goToFormat}>
              Cambiar formato
            </Button>
            <Button
              disabled={busy || exportable === 0}
              onClick={confirm}
              variant="contained"
            >
              Confirmar y descargar
            </Button>
          </>
        ) : null}
      </DialogActions>
    </Dialog>
  );
}
