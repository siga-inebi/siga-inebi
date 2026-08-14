import { useCallback, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";

import {
  ATTENDANCE_ALERT_LABEL,
  ATTENDANCE_ALERT_VARIANT,
  attendanceService,
  MOVEMENT_LABEL,
  MOVEMENT_VARIANT,
  ORIGIN_LABEL,
  ORIGIN_VARIANT,
  TRANSMISSION_LABEL,
} from "@attendance/attendanceService.js";
import { PAGE_SIZE } from "@academics/academicsService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDate, formatDateTime } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { CodeCell, MutedCell } from "@ui/table/cells.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";

import { DayStatusProbe } from "./DayStatusProbe.jsx";
import { JornadaParametersWindow } from "./JornadaParametersWindow.jsx";

const EVENT_COLUMNS = [
  {
    key: "student_id",
    label: "Estudiante",
    render: (row) => <CodeCell value={row.student_id} />,
  },
  {
    key: "shift_id",
    label: "Jornada",
    render: (row) => <CodeCell value={row.shift_id} />,
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
    label: "Transmision",
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

const ALERT_COLUMNS = [
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
    key: "student_id",
    label: "Estudiante",
    render: (row) => <CodeCell value={row.student_id} />,
  },
  {
    key: "event_date",
    label: "Fecha",
    render: (row) => formatDate(row.event_date),
  },
  {
    key: "section_id",
    label: "Seccion",
    render: (row) =>
      row.section_id ? (
        <CodeCell value={row.section_id} />
      ) : (
        <MutedCell>Sin seccion</MutedCell>
      ),
  },
  {
    key: "created_at",
    label: "Emitida",
    render: (row) => formatDateTime(row.created_at),
  },
];

const EVENT_FIELDS = [
  { name: "student_id", label: "ID de estudiante", required: true },
  { name: "shift_id", label: "ID de jornada", required: true },
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
    options: [
      { value: "manual", label: "Manual" },
      { value: "scan", label: "Lectura" },
      { value: "declared", label: "Declarada" },
    ],
    required: true,
  },
  {
    name: "captured_at",
    label: "Momento de captura",
    type: "date",
    required: true,
    help: "El backend registra la hora de captura; la fecha del movimiento puede ser anterior.",
  },
];

/**
 * Asistencia: eventos de entrada y salida, alertas de la jornada y consulta del
 * estado del dia.
 *
 * Los eventos NO se editan ni se borran: el backend suprime duplicados marcando
 * `is_active=false` y conserva el registro. La columna "Vigente" existe para que
 * eso sea visible en vez de parecer que un movimiento desaparecio.
 */
export function AttendancePage() {
  const loadEvents = useCallback(
    (params) => attendanceService.listEvents(params),
    []
  );
  const loadAlerts = useCallback(
    (params) => attendanceService.listAlerts(params),
    []
  );

  // Paginacion del servidor: el registro de movimientos crece con cada dia de
  // clases, asi que traerlo completo para filtrar en memoria no escala.
  const events = usePaginatedList(loadEvents, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });
  const alerts = usePaginatedList(loadAlerts, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  const [creating, setCreating] = useState(false);
  const [showParameters, setShowParameters] = useState(false);

  const handleCreateEvent = async (payload) => {
    await attendanceService.createEvent(payload);
    setCreating(false);
    events.refresh();
    // Un movimiento nuevo puede resolver o generar alertas del dia.
    alerts.refresh();
  };

  return (
    <>
      <PageHeader
        action={
          <Stack direction="row" gap={1}>
            <Button
              onClick={() => setShowParameters(true)}
              startIcon={<TuneOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              Parametros de jornada
            </Button>
            <Button
              onClick={() => setCreating(true)}
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Registrar movimiento
            </Button>
          </Stack>
        }
        breadcrumb="Control de asistencia"
        subtitle="Movimientos de entrada y salida, alertas de la jornada y consulta del estado del dia de un estudiante."
        title="Asistencia"
      />

      <Grid container spacing={2} sx={{ mb: 1 }}>
        <Grid size={{ xs: 12, lg: 5 }}>
          <DayStatusProbe />
        </Grid>
        <Grid size={{ xs: 12, lg: 7 }}>
          <SectionCard
            subtitle="Emitidas por el cierre de jornada"
            title="Alertas de asistencia"
          >
            {alerts.error ? (
              <Alert severity="error" sx={{ m: 2 }}>
                {alerts.error}
              </Alert>
            ) : null}
            <SectionTableArea>
              <DataTable
                columns={ALERT_COLUMNS}
                emptyMessage="Sin alertas de asistencia registradas."
                getRowKey={(row) => row.public_id}
                loading={alerts.loading}
                pagination={alerts.pagination}
                rows={alerts.items}
              />
            </SectionTableArea>
          </SectionCard>
        </Grid>
      </Grid>

      <SectionCard
        fillHeight
        subtitle="Registro completo, duplicados incluidos"
        title="Movimientos"
      >
        {events.error ? (
          <Alert severity="error" sx={{ m: 2 }}>
            {events.error}
          </Alert>
        ) : null}
        <SectionTableArea>
          <DataTable
            columns={EVENT_COLUMNS}
            emptyMessage="Todavia no hay movimientos registrados."
            fillHeight
            getRowKey={(row) => row.public_id}
            loading={events.loading}
            pagination={events.pagination}
            rows={events.items}
          />
        </SectionTableArea>
      </SectionCard>

      <EntityFormWindow
        description="Un movimiento manual queda marcado con origen distinto al de lectura, para poder auditarlo despues."
        fields={EVENT_FIELDS}
        initialValues={{
          student_id: "",
          shift_id: "",
          event_date: "",
          movement_type: "entry",
          origin: "manual",
          captured_at: "",
        }}
        key={creating ? "event-create-open" : "event-create-closed"}
        onCancel={() => setCreating(false)}
        onSubmit={handleCreateEvent}
        open={creating}
        submitLabel="Registrar movimiento"
        title="Nuevo movimiento de asistencia"
      />

      {showParameters ? (
        <JornadaParametersWindow onClose={() => setShowParameters(false)} />
      ) : null}
    </>
  );
}
