import { useCallback, useMemo, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";

import { PAGE_SIZE } from "@academics/academicsService.js";
import { reportingService } from "@reporting/reportingService.js";
import {
  labelIndex,
  useCycleCatalog,
  useShiftCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDate } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { CodeCell, MutedCell } from "@ui/table/cells.jsx";

const thresholdColumns = (shiftNames) => [
  {
    key: "shift_id",
    label: "Jornada",
    render: (row) =>
      shiftNames.get(row.shift_id) ??
      (row.shift_id ? (
        <CodeCell value={row.shift_id} />
      ) : (
        <MutedCell>—</MutedCell>
      )),
  },
  {
    key: "academic_cycle_id",
    label: "Ciclo",
    render: (row) => <CodeCell value={row.academic_cycle_id} />,
  },
  {
    key: "max_absences",
    label: "Ausencias maximas",
    align: "right",
    render: (row) => row.max_absences,
  },
  {
    key: "lookback_days",
    label: "Ventana",
    align: "right",
    render: (row) => `${row.lookback_days} dias`,
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

const thresholdFields = ({ cycles, shifts }) => [
  {
    name: "shift_id",
    label: "Jornada",
    type: "select",
    options: shifts.options,
    loading: shifts.loading,
    optionsError: shifts.error,
    emptyHint: "No hay jornadas registradas.",
    required: true,
  },
  {
    name: "academic_cycle_id",
    label: "Ciclo escolar",
    type: "select",
    options: cycles.options,
    loading: cycles.loading,
    optionsError: cycles.error,
    emptyHint: "No hay ciclos escolares registrados.",
    required: true,
  },
  {
    name: "max_absences",
    label: "Ausencias maximas",
    type: "number",
    min: 1,
    required: true,
    help: "Al superarlo se emite una alerta de frecuencia de ausencias.",
  },
  {
    name: "lookback_days",
    label: "Ventana de dias",
    type: "number",
    min: 1,
    required: true,
    help: "Periodo hacia atras sobre el que se cuentan las ausencias.",
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
 * Umbrales que disparan la alerta de frecuencia de ausencias.
 *
 * Igual que los parametros de jornada: no se editan, se reemplazan registrando
 * un umbral nuevo con vigencia posterior, y los anteriores quedan como historia
 * para poder explicar por que se emitio una alerta en su momento.
 */
export function AbsenceThresholdsWindow({ onClose }) {
  const cycles = useCycleCatalog();
  const shifts = useShiftCatalog();
  const shiftNames = useMemo(
    () => labelIndex(shifts.options),
    [shifts.options]
  );

  const loadThresholds = useCallback(
    (params) => reportingService.listAbsenceThresholds(params),
    []
  );
  const list = usePaginatedList(loadThresholds, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  const [creating, setCreating] = useState(false);

  const handleCreate = async (payload) => {
    await reportingService.createAbsenceThreshold(payload);
    setCreating(false);
    list.refresh();
  };

  return (
    <>
      <FloatingWindow
        description="Cuantas ausencias, y en cuantos dias, hacen falta para que el sistema emita una alerta."
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
              Nuevo umbral
            </Button>
          </>
        }
        onClose={onClose}
        open
        title="Umbrales de ausencia"
        width={WINDOW_WIDTH.wide}
      >
        <Stack gap={2}>
          {list.error ? <Alert severity="error">{list.error}</Alert> : null}
          <DataTable
            columns={thresholdColumns(shiftNames)}
            emptyMessage="Todavia no hay umbrales configurados."
            getRowKey={(row) => row.public_id}
            loading={list.loading}
            pagination={list.pagination}
            rows={list.items}
          />
        </Stack>
      </FloatingWindow>

      {creating ? (
        <EntityFormWindow
          description="El umbral aplica a una jornada y un ciclo concretos."
          fields={thresholdFields({ cycles, shifts })}
          initialValues={{
            shift_id: "",
            academic_cycle_id: "",
            max_absences: 3,
            lookback_days: 30,
            effective_from: "",
          }}
          key="threshold-create"
          onCancel={() => setCreating(false)}
          onSubmit={handleCreate}
          open
          submitLabel="Registrar umbral"
          title="Nuevo umbral de ausencia"
        />
      ) : null}
    </>
  );
}
