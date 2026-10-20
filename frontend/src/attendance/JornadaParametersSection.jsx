import { useMemo, useState } from "react";

import Button from "@mui/material/Button";
import AddIcon from "@mui/icons-material/Add";

import {
  attendanceService,
  withoutBlank,
} from "@attendance/attendanceService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import {
  labelIndex,
  useCycleCatalog,
  useShiftCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { formatDate } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { CodeCell, MutedCell } from "@ui/table/cells.jsx";

/** "07:00:00" → "07:00". */
const shortTime = (value) => (value ? String(value).slice(0, 5) : "");

/** Días lectivos: 1 = lunes … 7 = domingo (RF-JOR-001). */
const SCHOOL_DAY_PRESETS = [
  { value: "1,2,3,4,5", label: "Lunes a viernes" },
  { value: "1,2,3,4,5,6", label: "Lunes a sábado" },
  { value: "1,2,3,4,5,6,7", label: "Todos los días" },
];
const DAY_NAMES = ["", "lun", "mar", "mié", "jue", "vie", "sáb", "dom"];

function schoolDaysLabel(days) {
  const key = (days ?? []).join(",");
  return (
    SCHOOL_DAY_PRESETS.find((preset) => preset.value === key)?.label ??
    (days ?? []).map((day) => DAY_NAMES[day]).join(", ")
  );
}

const parameterColumns = (shiftNames) => [
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
    key: "entry_limit_time",
    label: "Límite de entrada",
    render: (row) => shortTime(row.entry_limit_time),
  },
  {
    key: "tolerance_minutes",
    label: "Tolerancia",
    align: "right",
    render: (row) => `${row.tolerance_minutes} min`,
  },
  {
    key: "closing_time",
    label: "Cierre",
    render: (row) => shortTime(row.closing_time),
  },
  {
    key: "school_days",
    label: "Días lectivos",
    render: (row) => schoolDaysLabel(row.school_days),
  },
  {
    key: "duplicate_suppression_minutes",
    label: "Supresión de duplicados",
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

const parameterFields = ({ cycles, shifts }) => [
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
    // Campo de hora nativo en vez de texto con formato dictado: el navegador ya
    // sabe validar una hora, y "HH:MM" como instruccion es un error esperando.
    name: "opening_time",
    label: "Hora de apertura",
    type: "time",
    help: "Desde cuándo se reciben escaneos. Si se deja vacía, desde las 00:00.",
  },
  {
    name: "entry_limit_time",
    label: "Hora límite de entrada",
    type: "time",
    required: true,
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
    type: "time",
    required: true,
  },
  {
    name: "duplicate_suppression_minutes",
    label: "Supresión de duplicados (minutos)",
    type: "number",
    min: 0,
    required: true,
    help: "Dos lecturas del mismo estudiante dentro de esta ventana cuentan como una.",
  },
  {
    name: "school_days",
    label: "Días lectivos",
    type: "select",
    options: SCHOOL_DAY_PRESETS,
    required: true,
  },
  {
    name: "effective_from",
    label: "Vigente desde",
    type: "date",
    required: true,
  },
];

/**
 * Parámetros de jornada por sede y ciclo (RF-JOR-001).
 *
 * No hay edición: registrar parámetros nuevos con una vigencia posterior es lo
 * que los reemplaza, y los anteriores se conservan como historia. Por eso la
 * tabla muestra también los reemplazados.
 */
export function JornadaParametersSection() {
  const cycles = useCycleCatalog();
  const shifts = useShiftCatalog();
  const shiftNames = useMemo(
    () => labelIndex(shifts.options),
    [shifts.options]
  );

  const list = useServerList({
    queryKey: queryKeys.attendance("jornada-parameters"),
    fetchPage: (params) => attendanceService.listJornadaParameters(params),
    urlPrefix: "par_",
  });

  const [creating, setCreating] = useState(false);

  const handleCreate = async ({ school_days, ...payload }) => {
    await attendanceService.createJornadaParameters({
      ...withoutBlank(payload),
      school_days: school_days.split(",").map(Number),
    });
    setCreating(false);
  };

  return (
    <>
      <ListSection
        action={
          <Button
            onClick={() => setCreating(true)}
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nuevos parámetros
          </Button>
        }
        columns={parameterColumns(shiftNames)}
        emptyMessage="Todavía no hay parámetros de jornada registrados."
        getRowKey={(row) => row.public_id}
        list={list}
        showInactiveToggle={false}
        subtitle="Horarios y tolerancias del cálculo de asistencia. Un registro nuevo con vigencia posterior reemplaza al anterior; nada se borra."
        title="Parámetros de jornada"
      />

      {creating ? (
        <EntityFormWindow
          description="Estos valores definen desde cuándo una entrada cuenta como tardanza, qué días se reciben escaneos y cuándo se cierra la jornada."
          fields={parameterFields({ cycles, shifts })}
          initialValues={{
            shift_id: "",
            academic_cycle_id: "",
            opening_time: "",
            entry_limit_time: "",
            tolerance_minutes: 0,
            closing_time: "",
            duplicate_suppression_minutes: 0,
            school_days: "1,2,3,4,5",
            effective_from: "",
          }}
          onCancel={() => setCreating(false)}
          onSubmit={handleCreate}
          open
          submitLabel="Registrar parámetros"
          title="Nuevos parámetros de jornada"
        />
      ) : null}
    </>
  );
}
