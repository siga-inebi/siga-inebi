import { useCallback, useMemo, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";

import { PAGE_SIZE } from "@academics/academicsService.js";
import { evaluationService } from "@evaluation/evaluationService.js";
import {
  asTeacherPersonOptions,
  labelIndex,
  useSubjectCatalog,
  useTeacherCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDateTime } from "@shared/utils/format.js";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { CodeCell, MutedCell } from "@ui/table/cells.jsx";

/** Nombre del catalogo, con el identificador crudo como respaldo. */
function nameCell(index, id) {
  return (
    index.get(id) ?? (id ? <CodeCell value={id} /> : <MutedCell>—</MutedCell>)
  );
}

const exceptionColumns = (names) => [
  {
    key: "subject",
    label: "Curso",
    render: (row) => nameCell(names.subjects, row.subject),
  },
  {
    key: "teacher",
    label: "Docente",
    render: (row) => nameCell(names.teachers, row.teacher),
  },
  { key: "reason", label: "Motivo", render: (row) => row.reason },
  {
    key: "expires_at",
    label: "Vence",
    render: (row) => formatDateTime(row.expires_at),
  },
  {
    key: "created_at",
    label: "Otorgado",
    render: (row) => formatDateTime(row.created_at),
  },
];

const exceptionFields = ({ subjects, teacherPeople, teachers }) => [
  {
    name: "subject",
    label: "Curso",
    type: "select",
    options: subjects.options,
    loading: subjects.loading,
    optionsError: subjects.error,
    emptyHint: "No hay cursos registrados.",
    required: true,
  },
  {
    name: "teacher",
    label: "Docente",
    type: "select",
    options: teacherPeople,
    loading: teachers.loading,
    optionsError: teachers.error,
    emptyHint: "No hay docentes registrados.",
    required: true,
  },
  {
    name: "reason",
    label: "Motivo de la excepcion",
    required: true,
    span: "full",
    help: "Queda registrado en la auditoria: describe por que se abre la captura fuera de ventana.",
  },
  {
    name: "expires_at",
    label: "Vence el",
    type: "date",
    required: true,
    help: "La excepcion caduca sola en esta fecha; no hay que revocarla a mano.",
  },
];

/**
 * Permisos excepcionales de captura fuera de ventana de una unidad (RF-EVC-004).
 *
 * Solo se otorgan y caducan: no hay revocacion manual porque el vencimiento es
 * obligatorio, y no hay edicion porque cambiar el motivo despues destruiria la
 * evidencia de por que se autorizo.
 */
export function CaptureExceptionsWindow({ cycleId, onClose, unit }) {
  const subjects = useSubjectCatalog();
  const teachers = useTeacherCatalog();

  const teacherPeople = useMemo(
    () => asTeacherPersonOptions(teachers.options),
    [teachers.options]
  );
  const names = useMemo(
    () => ({
      subjects: labelIndex(subjects.options),
      teachers: labelIndex(teacherPeople),
    }),
    [subjects.options, teacherPeople]
  );

  const loadExceptions = useCallback(
    (params) =>
      evaluationService.listCaptureExceptions(cycleId, unit.public_id, params),
    [cycleId, unit.public_id]
  );
  const list = usePaginatedList(loadExceptions, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  const [granting, setGranting] = useState(false);

  const handleGrant = async (payload) => {
    await evaluationService.createCaptureException(
      cycleId,
      unit.public_id,
      payload
    );
    setGranting(false);
    list.refresh();
  };

  return (
    <>
      <FloatingWindow
        description={`Autorizaciones para capturar notas de "${unit.name}" fuera de su ventana normal. Cada una vence por si sola.`}
        footer={
          <>
            <Button onClick={onClose} variant="text">
              Cerrar
            </Button>
            <Button
              onClick={() => setGranting(true)}
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Otorgar excepcion
            </Button>
          </>
        }
        onClose={onClose}
        open
        title="Permisos excepcionales de captura"
        width={WINDOW_WIDTH.wide}
      >
        <Stack gap={2}>
          {list.error ? <Alert severity="error">{list.error}</Alert> : null}
          <DataTable
            columns={exceptionColumns(names)}
            emptyMessage="Esta unidad no tiene permisos excepcionales otorgados."
            getRowKey={(row) => row.public_id}
            loading={list.loading}
            pagination={list.pagination}
            rows={list.items}
          />
        </Stack>
      </FloatingWindow>

      {granting ? (
        <EntityFormWindow
          description="El motivo y el vencimiento son obligatorios: la excepcion es auditable y temporal."
          fields={exceptionFields({ subjects, teacherPeople, teachers })}
          initialValues={{
            subject: "",
            teacher: "",
            reason: "",
            expires_at: "",
          }}
          key="grant-exception"
          onCancel={() => setGranting(false)}
          onSubmit={handleGrant}
          open
          submitLabel="Otorgar excepcion"
          title="Nueva excepcion de captura"
        />
      ) : null}
    </>
  );
}
