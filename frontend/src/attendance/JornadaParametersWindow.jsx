import { useCallback, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";

import { PAGE_SIZE } from "@academics/academicsService.js";
import { attendanceService } from "@attendance/attendanceService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDate } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { CodeCell } from "@ui/table/cells.jsx";

const PARAMETER_COLUMNS = [
  { key: "shift_id", label: "Jornada", render: (row) => <CodeCell value={row.shift_id} /> },
  {
    key: "entry_limit_time",
    label: "Limite de entrada",
    render: (row) => row.entry_limit_time,
  },
  {
    key: "tolerance_minutes",
    label: "Tolerancia",
    align: "right",
    render: (row) => `${row.tolerance_minutes} min`,
  },
  { key: "closing_time", label: "Cierre", render: (row) => row.closing_time },
  {
    key: "duplicate_suppression_minutes",
    label: "Supresion de duplicados",
    align: "right",
    render: (row) => `${row.duplicate_suppression_minutes} min`,
  },
  {
    key: "effective_from",
    label: "Vigente desde",
    render: (row) => formatDate(row.effective_from),
  },
  {
    key: "is_active",
    label: "Estado",
    render: (row) =>
      row.is_active === false ? (
        <StatusChip label="Reemplazado" variant="neutral" />
      ) : (
        <StatusChip label="Vigente" variant="success" />
      ),
  },
];

const PARAMETER_FIELDS = [
  { name: "shift_id", label: "ID de jornada", required: true },
  { name: "academic_cycle_id", label: "ID de ciclo escolar", required: true },
  {
    name: "entry_limit_time",
    label: "Hora limite de entrada",
    required: true,
    placeholder: "HH:MM",
    help: "Formato de 24 horas, por ejemplo 07:30.",
  },
  {
    name: "tolerance_minutes",
    label: "Tolerancia (minutos)",
    type: "number",
    min: 0,
    required: true,
  },
  {
    name: "closing_time",
    label: "Hora de cierre",
    required: true,
    placeholder: "HH:MM",
  },
  {
    name: "duplicate_suppression_minutes",
    label: "Supresion de duplicados (minutos)",
    type: "number",
    min: 0,
    required: true,
    help: "Dos lecturas del mismo estudiante dentro de esta ventana cuentan como una.",
  },
  {
    name: "effective_from",
    label: "Vigente desde",
    type: "date",
    required: true,
    span: "full",
  },
];

/**
 * Parametros de jornada por sede y ciclo (RF-JOR-001).
 *
 * No hay edicion: registrar parametros nuevos con una fecha de vigencia posterior
 * es lo que los reemplaza, y los anteriores se conservan como historia. Por eso la
 * tabla muestra tambien los reemplazados en vez de esconderlos.
 */
export function JornadaParametersWindow({ onClose }) {
  const loadParameters = useCallback(
    (params) => attendanceService.listJornadaParameters(params),
    []
  );
  const list = usePaginatedList(loadParameters, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  const [creating, setCreating] = useState(false);

  const handleCreate = async (payload) => {
    await attendanceService.createJornadaParameters(payload);
    setCreating(false);
    list.refresh();
  };

  return (
    <>
      <FloatingWindow
        description="Horarios y tolerancias que usa el calculo de asistencia. Un registro nuevo con vigencia posterior reemplaza al anterior; nada se borra."
        footer={
          <>
            <Button onClick={onClose} variant="text">
              Cerrar
            </Button>
            <Button
              onClick={() => setCreating(true)}
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Nuevos parametros
            </Button>
          </>
        }
        onClose={onClose}
        open
        title="Parametros de jornada"
        width={WINDOW_WIDTH.wide}
      >
        <Stack gap={2}>
          {list.error ? <Alert severity="error">{list.error}</Alert> : null}
          <DataTable
            columns={PARAMETER_COLUMNS}
            emptyMessage="Todavia no hay parametros de jornada registrados."
            getRowKey={(row) => row.public_id}
            loading={list.loading}
            pagination={list.pagination}
            rows={list.items}
          />
        </Stack>
      </FloatingWindow>

      {creating ? (
        <EntityFormWindow
          description="Estos valores definen desde cuando una entrada cuenta como tardanza y cuando se cierra la jornada."
          fields={PARAMETER_FIELDS}
          initialValues={{
            shift_id: "",
            academic_cycle_id: "",
            entry_limit_time: "",
            tolerance_minutes: 0,
            closing_time: "",
            duplicate_suppression_minutes: 0,
            effective_from: "",
          }}
          key="parameters-create"
          onCancel={() => setCreating(false)}
          onSubmit={handleCreate}
          open
          submitLabel="Registrar parametros"
          title="Nuevos parametros de jornada"
        />
      ) : null}
    </>
  );
}
