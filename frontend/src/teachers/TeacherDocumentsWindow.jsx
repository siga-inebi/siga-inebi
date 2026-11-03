import { useCallback, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";

import { documentsService } from "@documents/documentsService.js";
import { PAGE_SIZE } from "@academics/academicsService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDateTime } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";

/** Dispara la descarga del adjunto sin dejar la URL con token en pantalla. */
function triggerDownload(url) {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

/**
 * Expediente documental del docente (RF-DOC-001).
 *
 * Misma tuberia que el expediente del estudiante: el archivo se valida, se
 * guarda fuera de la base de datos con su SHA-256 y una sustitucion conserva el
 * historial. La descarga pide un token breve en cada clic.
 */
export function TeacherDocumentsWindow({ teacher, teacherName, onClose }) {
  const loadRecords = useCallback(
    (params) => documentsService.listTeacherRecords(teacher.public_id, params),
    [teacher.public_id]
  );
  const records = usePaginatedList(loadRecords, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });
  const [uploading, setUploading] = useState(false);
  const [downloadError, setDownloadError] = useState("");

  const handleUpload = async ({ file }) => {
    const payload = new FormData();
    payload.set("file", file);
    await documentsService.uploadTeacherRecord(teacher.public_id, payload);
    setUploading(false);
    records.refresh();
  };

  const handleDownload = async (record) => {
    setDownloadError("");
    try {
      const { download_url: url } = await documentsService.issueDownloadToken(
        record.public_id
      );
      triggerDownload(url);
    } catch (requestError) {
      setDownloadError(requestError.message);
    }
  };

  const columns = [
    { key: "filename", label: "Archivo", render: (row) => row.filename },
    {
      key: "version_number",
      label: "Versión",
      align: "right",
      render: (row) => `v${row.version_number}`,
    },
    {
      key: "status",
      label: "Estado",
      render: (row) => (
        <StatusChip
          label={row.status === "active" ? "Vigente" : "Histórico"}
          variant={row.status === "active" ? "success" : "neutral"}
        />
      ),
    },
    {
      key: "created_at",
      label: "Registrado",
      render: (row) => formatDateTime(row.created_at),
    },
    {
      key: "download",
      label: "",
      align: "right",
      render: (row) => (
        <Button
          aria-label={`Descargar ${row.filename}`}
          onClick={(event) => {
            event.stopPropagation();
            handleDownload(row);
          }}
          size="small"
          variant="text"
        >
          Descargar
        </Button>
      ),
    },
  ];

  return (
    <>
      <FloatingWindow
        description={`Documentos del expediente institucional de ${teacherName}.`}
        footer={
          <>
            <Button onClick={onClose} variant="text">
              Cerrar
            </Button>
            <Button
              onClick={() => setUploading(true)}
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Adjuntar documento
            </Button>
          </>
        }
        onClose={onClose}
        open
        title="Expediente documental del docente"
        width={WINDOW_WIDTH.wide}
      >
        <Stack gap={2}>
          {records.error ? (
            <Alert severity="warning">
              No se pudo consultar el expediente autorizado: {records.error}
            </Alert>
          ) : null}
          {downloadError ? (
            <Alert severity="error">{downloadError}</Alert>
          ) : null}
          <DataTable
            columns={columns}
            emptyMessage="Este docente no tiene documentos en su expediente."
            getRowKey={(row) => row.public_id}
            loading={records.loading}
            pagination={records.pagination}
            rows={records.items}
          />
        </Stack>
      </FloatingWindow>

      {uploading ? (
        <EntityFormWindow
          description="El archivo se valida, se guarda fuera de la base de datos y queda asociado al expediente del docente."
          fields={[
            {
              name: "file",
              label: "Documento",
              type: "file",
              accept: ".pdf,.jpg,.jpeg,.png",
              required: true,
            },
          ]}
          initialValues={{ file: null }}
          key="upload-teacher-document"
          onCancel={() => setUploading(false)}
          onSubmit={handleUpload}
          open
          submitLabel="Adjuntar documento"
          title="Adjuntar documento del docente"
        />
      ) : null}
    </>
  );
}
