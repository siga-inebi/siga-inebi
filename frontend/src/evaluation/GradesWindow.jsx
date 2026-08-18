import { useCallback, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";

import { PAGE_SIZE } from "@academics/academicsService.js";
import { evaluationService } from "@evaluation/evaluationService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDateTime } from "@shared/utils/format.js";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { CodeCell } from "@ui/table/cells.jsx";

const GRADE_COLUMNS = [
  {
    key: "enrolment",
    label: "Inscripcion",
    render: (row) => <CodeCell value={row.enrolment} />,
  },
  {
    key: "subject",
    label: "Subarea",
    render: (row) => <CodeCell value={row.subject} />,
  },
  { key: "value", label: "Nota", align: "right", render: (row) => row.value },
  {
    key: "updated_at",
    label: "Ultima actualizacion",
    render: (row) => formatDateTime(row.updated_at),
  },
];

const GRADE_FIELDS = [
  {
    name: "enrolment",
    label: "ID de inscripcion",
    type: "number",
    required: true,
  },
  { name: "subject", label: "ID de subarea", type: "number", required: true },
  { name: "teacher", label: "ID de docente", type: "number", required: true },
  {
    name: "value",
    label: "Nota",
    type: "number",
    min: 0,
    required: true,
    help: "Escala de 0 a 100. Nota ya calculada por el docente para esta unidad; el sistema no la deriva de actividades.",
  },
];

/**
 * Notas de una unidad de evaluacion (RF-CAL-001).
 *
 * Registrar de nuevo la misma inscripcion/subarea actualiza la nota existente
 * en vez de duplicarla: es el valor consolidado unico de esa combinacion. El
 * backend rechaza el registro si la ventana de captura esta cerrada y no hay
 * una excepcion vigente para ese docente y esa subarea.
 */
export function GradesWindow({ cycleId, onClose, unit }) {
  const loadGrades = useCallback(
    (params) => evaluationService.listGrades(cycleId, unit.public_id, params),
    [cycleId, unit.public_id]
  );
  const list = usePaginatedList(loadGrades, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  const [registering, setRegistering] = useState(false);

  const handleRegister = async (payload) => {
    await evaluationService.registerGrade(cycleId, unit.public_id, payload);
    setRegistering(false);
    list.refresh();
  };

  return (
    <>
      <FloatingWindow
        description={`Notas registradas para "${unit.name}". Volver a registrar la misma inscripcion y subarea actualiza la nota.`}
        footer={
          <>
            <Button onClick={onClose} variant="text">
              Cerrar
            </Button>
            <Button
              onClick={() => setRegistering(true)}
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Registrar nota
            </Button>
          </>
        }
        onClose={onClose}
        open
        title="Notas de la unidad"
        width={WINDOW_WIDTH.wide}
      >
        <Stack gap={2}>
          {list.error ? <Alert severity="error">{list.error}</Alert> : null}
          <DataTable
            columns={GRADE_COLUMNS}
            emptyMessage="Esta unidad todavia no tiene notas registradas."
            getRowKey={(row) => row.public_id}
            loading={list.loading}
            pagination={list.pagination}
            rows={list.items}
          />
        </Stack>
      </FloatingWindow>

      {registering ? (
        <EntityFormWindow
          description="La nota ya viene calculada por el docente: el sistema solo la almacena."
          fields={GRADE_FIELDS}
          initialValues={{ enrolment: "", subject: "", teacher: "", value: "" }}
          key="register-grade"
          onCancel={() => setRegistering(false)}
          onSubmit={handleRegister}
          open
          submitLabel="Registrar nota"
          title="Nueva nota de unidad"
        />
      ) : null}
    </>
  );
}
