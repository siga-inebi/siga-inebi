import { lazy, Suspense, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AttachFileIcon from "@mui/icons-material/AttachFile";

import { PERMISSION } from "@auth/permissions.js";
import {
  attendanceService,
  JUSTIFICATION_STATUS_LABEL,
  SITUATION_TYPE_LABEL,
} from "@attendance/attendanceService.js";
import { formatDate, formatDateTime } from "@shared/utils/format.js";
import { DetailField } from "@ui/layout/DetailWindow.jsx";

import { StudentCell } from "../StudentCell.jsx";
import { studentLabel } from "../studentSearch.js";
import { RequestQueue, StatusCell } from "./RequestQueue.jsx";

// Los formularios (y `EntityFormWindow`) se descargan al abrirlos.
const formsModule = () => import("./JustificationForms.jsx");
const AttachWindow = lazy(() =>
  formsModule().then((module) => ({ default: module.AttachWindow }))
);
const NewJustificationWindow = lazy(() =>
  formsModule().then((module) => ({ default: module.NewJustificationWindow }))
);

function formatSize(bytes) {
  if (bytes == null) return "";
  return bytes >= 1024 * 1024
    ? `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

/**
 * Adjunto en el detalle. Ver el adjunto consulta sus datos y queda en la
 * bitácora (puede traer información de salud), así que no se pide hasta que la
 * persona lo decide.
 */
function AttachmentPanel({ canResolve, justification, user }) {
  const isSubmitter =
    Boolean(user?.public_id) &&
    justification.submitted_by?.public_id === user.public_id;
  const [attachment, setAttachment] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [attaching, setAttaching] = useState(false);
  const [attached, setAttached] = useState(false);

  const view = async () => {
    setLoading(true);
    setError("");
    try {
      setAttachment(
        await attendanceService.getJustificationAttachment(
          justification.public_id
        )
      );
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  const hasAttachment = justification.has_attachment || attached;

  return (
    <Stack gap={1.5} sx={{ mt: 2.5 }}>
      {hasAttachment && (isSubmitter || canResolve) && !attachment ? (
        <Box>
          <Button
            disabled={loading}
            onClick={view}
            startIcon={<AttachFileIcon fontSize="small" />}
            variant="outlined"
          >
            {loading ? "Consultando…" : "Ver adjunto"}
          </Button>
        </Box>
      ) : null}
      {hasAttachment && !attachment ? (
        <Alert severity="info">
          Consultar el adjunto queda registrado en la bitácora de auditoría.
        </Alert>
      ) : null}
      {attachment ? (
        <Box
          component="dl"
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
            gap: 2,
            m: 0,
          }}
        >
          <DetailField label="Archivo" value={attachment.filename} />
          <DetailField label="Tipo" value={attachment.content_type} />
          <DetailField
            label="Tamaño"
            value={formatSize(attachment.size_bytes)}
          />
          <DetailField
            label="Adjuntado"
            value={formatDateTime(attachment.created_at)}
          />
        </Box>
      ) : null}
      {!hasAttachment && isSubmitter ? (
        <Box>
          <Button
            onClick={() => setAttaching(true)}
            startIcon={<AttachFileIcon fontSize="small" />}
            variant="outlined"
          >
            Adjuntar documento
          </Button>
        </Box>
      ) : null}
      {error ? (
        <Alert role="alert" severity="error">
          {error}
        </Alert>
      ) : null}
      <Suspense fallback={null}>
        {attaching ? (
          <AttachWindow
            justification={justification}
            onCancel={() => setAttaching(false)}
            onDone={() => {
              setAttaching(false);
              setAttached(true);
            }}
            title="Adjuntar documento"
          />
        ) : null}
      </Suspense>
    </Stack>
  );
}

const JUSTIFICATION_QUEUE = {
  kind: "justifications",
  prefix: "jus_",
  title: "Justificaciones",
  subtitle: "Pendientes primero; las que puede revisar y las que presentó.",
  noun: "justificación",
  theNoun: "la justificación",
  detailTitle: "Justificación",
  newLabel: "Nueva justificación",
  createdNotice: "Justificación presentada; queda pendiente de resolver.",
  emptyMessage: "Sin justificaciones para los filtros seleccionados.",
  statusLabels: JUSTIFICATION_STATUS_LABEL,
  requestPermission: PERMISSION.ATTENDANCE_JUSTIFICATION_REQUEST,
  resolvePermission: PERMISSION.ATTENDANCE_JUSTIFICATION_RESOLVE,
  list: (params) => attendanceService.listJustifications(params),
  get: (id) => attendanceService.getJustification(id),
  resolve: (id, payload) => attendanceService.resolveJustification(id, payload),
  columns: [
    {
      key: "student",
      label: "Estudiante",
      render: (row) => <StudentCell student={row.student} />,
    },
    {
      key: "absence_date",
      label: "Fecha",
      render: (row) => formatDate(row.absence_date),
    },
    {
      key: "situation_type",
      label: "Situación",
      render: (row) =>
        row.situation_type_display ??
        SITUATION_TYPE_LABEL[row.situation_type] ??
        row.situation_type,
    },
    {
      key: "reason",
      label: "Motivo",
      render: (row) => row.reason_catalog?.name ?? row.reason,
    },
    {
      key: "status",
      label: "Estado",
      render: (row) => (
        <StatusCell labels={JUSTIFICATION_STATUS_LABEL} row={row} />
      ),
    },
    {
      key: "has_attachment",
      label: "Adjunto",
      render: (row) => (row.has_attachment ? "Sí" : "No"),
    },
    {
      key: "submitted_at",
      label: "Presentada",
      render: (row) => formatDateTime(row.submitted_at),
    },
  ],
  detailFields: (row) => [
    { label: "Estudiante", value: studentLabel(row.student) },
    { label: "Fecha de la inasistencia", value: formatDate(row.absence_date) },
    {
      label: "Situación",
      value:
        row.situation_type_display ?? SITUATION_TYPE_LABEL[row.situation_type],
    },
    { label: "Motivo del catálogo", value: row.reason_catalog?.name },
    { label: "Motivo", value: row.reason },
    {
      label: "Estado",
      value: <StatusCell labels={JUSTIFICATION_STATUS_LABEL} row={row} />,
    },
    {
      label: "Presentada por",
      value: [row.submitted_by?.name, formatDateTime(row.submitted_at)]
        .filter(Boolean)
        .join(" · "),
    },
    {
      label: "Excepción al plazo",
      value: row.is_exception ? row.exception_reason || "Sí" : "No",
    },
    {
      label: "Resuelta por",
      value: row.resolved_by
        ? `${row.resolved_by.name} · ${formatDateTime(row.resolved_at)}`
        : null,
    },
    { label: "Comentario de la resolución", value: row.resolution_comment },
  ],
  renderDetailExtras: (row, context) => (
    <AttachmentPanel
      canResolve={context.canResolve}
      justification={row}
      user={context.user}
    />
  ),
  renderCreate: (props) => (
    <Suspense fallback={null}>
      <NewJustificationWindow {...props} />
    </Suspense>
  ),
};

/** Bandeja de justificaciones (AS3). */
export function JustificationsQueue() {
  return <RequestQueue config={JUSTIFICATION_QUEUE} />;
}
