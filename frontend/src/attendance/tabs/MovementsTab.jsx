import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";

import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import {
  ATTENDANCE_ALERT_LABEL,
  ATTENDANCE_ALERT_VARIANT,
  attendanceService,
  MOVEMENT_LABEL,
  MOVEMENT_VARIANT,
  ORIGIN_LABEL,
  ORIGIN_VARIANT,
  TRANSMISSION_LABEL,
  withoutBlank,
} from "@attendance/attendanceService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import {
  labelIndex,
  useSectionCatalog,
  useShiftCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import {
  formatDate,
  formatDateTime,
  todayInputValue,
} from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { RemoteSearchSelect } from "@ui/forms/RemoteSearchSelect.jsx";
import { MutedCell, NameCell } from "@ui/table/cells.jsx";

import { StudentCell } from "../StudentCell.jsx";
import { STUDENT_SEARCH } from "../studentSearch.js";

const P = PERMISSION;

const eventColumns = (shiftNames) => [
  {
    key: "student",
    label: "Estudiante",
    render: (row) => <StudentCell student={row.student} />,
  },
  {
    key: "shift_id",
    label: "Jornada",
    render: (row) => <NameCell id={row.shift_id} index={shiftNames} />,
  },
  {
    key: "event_date",
    label: "Fecha",
    render: (row) => formatDate(row.event_date),
  },
  {
    key: "movement_type",
    label: "Movimiento",
    render: (row) => (
      <StatusChip
        label={MOVEMENT_LABEL[row.movement_type] ?? row.movement_type}
        variant={MOVEMENT_VARIANT[row.movement_type] ?? "neutral"}
      />
    ),
  },
  {
    key: "origin",
    label: "Origen",
    render: (row) => (
      <StatusChip
        label={ORIGIN_LABEL[row.origin] ?? row.origin}
        variant={ORIGIN_VARIANT[row.origin] ?? "neutral"}
      />
    ),
  },
  {
    key: "transmission",
    label: "Transmisión",
    render: (row) =>
      row.transmission ? (
        (TRANSMISSION_LABEL[row.transmission] ?? row.transmission)
      ) : (
        <MutedCell>Sin dato</MutedCell>
      ),
  },
  {
    key: "captured_at",
    label: "Capturado",
    render: (row) => formatDateTime(row.captured_at),
  },
  {
    key: "is_active",
    label: "Vigente",
    render: (row) =>
      row.is_active === false ? (
        <StatusChip label="Suprimido" variant="neutral" />
      ) : (
        <StatusChip label="Vigente" variant="success" />
      ),
  },
];

const alertColumns = (sectionNames) => [
  {
    key: "alert_type",
    label: "Alerta",
    render: (row) => (
      <StatusChip
        label={ATTENDANCE_ALERT_LABEL[row.alert_type] ?? row.alert_type}
        variant={ATTENDANCE_ALERT_VARIANT[row.alert_type] ?? "warning"}
      />
    ),
  },
  {
    key: "student",
    label: "Estudiante",
    render: (row) => <StudentCell student={row.student} />,
  },
  {
    key: "event_date",
    label: "Fecha",
    render: (row) => formatDate(row.event_date),
  },
  {
    key: "section_id",
    label: "Sección",
    render: (row) =>
      row.section_id ? (
        <NameCell id={row.section_id} index={sectionNames} />
      ) : (
        <MutedCell>Sin sección</MutedCell>
      ),
  },
  {
    key: "created_at",
    label: "Emitida",
    render: (row) => formatDateTime(row.created_at),
  },
];

/** Orígenes que la cuenta puede registrar a mano, según su permiso. */
const ORIGIN_OPTIONS = [
  ["manual", "Manual", P.ATTENDANCE_RECORD_MANUAL],
  ["scan", "Lectura", P.ATTENDANCE_SCAN],
  ["declared", "Declarada", P.ATTENDANCE_DECLARED_CLOSE],
];

const eventFields =
  ({ origins, reasons, shifts }) =>
  (values) => [
    {
      name: "student_id",
      label: "Estudiante",
      type: "search-select",
      search: STUDENT_SEARCH,
      help: "Escriba el nombre o el código del estudiante.",
      required: true,
    },
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
      name: "event_date",
      label: "Fecha del movimiento",
      type: "date",
      required: true,
    },
    {
      name: "movement_type",
      label: "Movimiento",
      type: "select",
      options: [
        { value: "entry", label: "Entrada" },
        { value: "exit", label: "Salida" },
      ],
      required: true,
    },
    {
      name: "origin",
      label: "Origen",
      type: "select",
      options: origins,
      required: true,
    },
    // RF-ASI-012: un movimiento manual exige un motivo vigente del catálogo.
    ...(values.origin === "manual"
      ? [
          {
            name: "manual_reason_id",
            label: "Motivo",
            type: "select",
            options: reasons.options,
            loading: reasons.loading,
            optionsError: reasons.error,
            emptyHint:
              "No hay motivos de registro manual vigentes. Pídalos a administración.",
            required: true,
          },
        ]
      : []),
    {
      name: "captured_at",
      label: "Momento de captura",
      type: "date",
      required: true,
      help: "El backend registra la hora de captura; la fecha del movimiento puede ser anterior.",
    },
  ];

function useManualReasons(enabled) {
  const query = useQuery({
    queryKey: queryKeys.attendance("manual-reasons"),
    queryFn: () => attendanceService.listManualReasons({ page_size: 100 }),
    enabled,
  });
  return {
    options: (query.data?.results ?? []).map((reason) => ({
      value: reason.public_id,
      label: reason.name,
    })),
    loading: enabled && query.isPending,
    error: query.error?.message ?? "",
  };
}

/**
 * Movimientos (AS5, AS6): el registro completo de entradas y salidas, las
 * alertas que emite el cierre de jornada y el registro manual.
 *
 * Los movimientos NO se editan ni se borran: el backend suprime duplicados con
 * `is_active=false` y conserva el registro; la columna "Vigente" lo muestra.
 */
export function MovementsTab() {
  const { can } = usePermissions();
  const origins = ORIGIN_OPTIONS.filter(([, , code]) => can(code)).map(
    ([value, label]) => ({ value, label })
  );
  const canRegister = origins.length > 0;
  const canView = can(P.STUDENT_VIEW_BASIC);

  const shifts = useShiftCatalog();
  const sections = useSectionCatalog();
  const shiftNames = useMemo(
    () => labelIndex(shifts.options),
    [shifts.options]
  );
  const sectionNames = useMemo(
    () => labelIndex(sections.options),
    [sections.options]
  );

  const [creating, setCreating] = useState(false);
  const reasons = useManualReasons(creating);

  const events = useServerList({
    queryKey: queryKeys.attendance("events"),
    fetchPage: (params) => attendanceService.listEvents(params),
    defaultFilters: { student_id: "" },
    urlPrefix: "mov_",
    enabled: canView,
  });
  const alerts = useServerList({
    queryKey: queryKeys.attendance("alerts"),
    fetchPage: (params) => attendanceService.listAlerts(params),
    urlPrefix: "al_",
    enabled: canView,
  });

  const handleCreate = async (payload) => {
    await attendanceService.createEvent(withoutBlank(payload));
    setCreating(false);
  };

  return (
    <Stack gap={2}>
      {canView ? (
        <ListSection
          action={
            canRegister ? (
              <Button
                onClick={() => setCreating(true)}
                startIcon={<AddIcon fontSize="small" />}
                variant="contained"
              >
                Registrar movimiento
              </Button>
            ) : null
          }
          columns={eventColumns(shiftNames)}
          emptyMessage={
            events.filters.student_id
              ? "Sin movimientos para el estudiante elegido."
              : "Todavía no hay movimientos registrados."
          }
          filters={
            <FilterBar>
              <RemoteSearchSelect
                label="Estudiante"
                name="student_id"
                onChange={(event) =>
                  events.setFilter("student_id", event.target.value)
                }
                search={STUDENT_SEARCH}
                value={events.filters.student_id}
              />
            </FilterBar>
          }
          getRowKey={(row) => row.public_id}
          list={events}
          showInactiveToggle={false}
          subtitle="Registro completo, duplicados incluidos."
          title="Movimientos"
        />
      ) : (
        <Stack direction="row" justifyContent="flex-end">
          {canRegister ? (
            <Button
              onClick={() => setCreating(true)}
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Registrar movimiento
            </Button>
          ) : null}
        </Stack>
      )}

      {canView ? (
        <ListSection
          columns={alertColumns(sectionNames)}
          emptyMessage="Sin alertas de asistencia registradas."
          getRowKey={(row) => row.public_id}
          list={alerts}
          showInactiveToggle={false}
          subtitle="Emitidas por el cierre de jornada."
          title="Alertas de asistencia"
        />
      ) : null}

      {creating ? (
        <EntityFormWindow
          description="Un movimiento manual queda marcado con su origen y su motivo, para poder auditarlo después."
          fields={eventFields({ origins, reasons, shifts })}
          // Las dos fechas arrancan en hoy: un movimiento se registra el día
          // que ocurre, y se pueden corregir si se carga algo atrasado.
          initialValues={{
            student_id: "",
            shift_id: "",
            event_date: todayInputValue(),
            movement_type: "entry",
            origin: origins[0]?.value ?? "",
            manual_reason_id: "",
            captured_at: todayInputValue(),
          }}
          onCancel={() => setCreating(false)}
          onSubmit={handleCreate}
          open
          submitLabel="Registrar movimiento"
          title="Nuevo movimiento de asistencia"
        />
      ) : null}
    </Stack>
  );
}
