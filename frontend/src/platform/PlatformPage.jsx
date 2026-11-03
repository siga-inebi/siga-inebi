import Alert from "@mui/material/Alert";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { formatDateTime } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

import {
  BACKUP_STACK_LABEL,
  TASK_STATUS_LABEL,
  TASK_STATUS_VARIANT,
  formatBytes,
  formatDuration,
  platformService,
} from "./platformService.js";

const TASK_STATUS_OPTIONS = Object.entries(TASK_STATUS_LABEL).map(
  ([value, label]) => ({
    value,
    label,
  })
);

function TaskStatus({ status }) {
  if (!status) return <MutedCell>Sin ejecuciones</MutedCell>;
  return (
    <StatusChip
      label={TASK_STATUS_LABEL[status] ?? status}
      variant={TASK_STATUS_VARIANT[status] ?? "neutral"}
    />
  );
}

function ServiceHealth() {
  const api = useResourceQuery([...queryKeys.platform.all, "api"], () =>
    platformService.apiHealth()
  );
  const database = useResourceQuery(
    [...queryKeys.platform.all, "database"],
    () => platformService.databaseHealth()
  );
  const row = (label, query) => (
    <Stack alignItems="center" direction="row" gap={1}>
      <Typography sx={{ minWidth: 120 }} variant="body2">
        {label}
      </Typography>
      {query.error ? (
        <StatusChip label="Sin respuesta" variant="danger" />
      ) : (
        <StatusChip
          label={query.data?.status === "ok" ? "Operativo" : "Verificando…"}
          variant={query.data?.status === "ok" ? "success" : "neutral"}
        />
      )}
    </Stack>
  );
  return (
    <SectionCard title="Servicio">
      <Stack gap={1.5} sx={{ px: 3, py: 2.5 }}>
        {row("API", api)}
        {row("Base de datos", database)}
      </Stack>
    </SectionCard>
  );
}

function BackupHealth() {
  const { data, error, loading } = useResourceQuery(
    queryKeys.platform.backupHealth(),
    () => platformService.backupHealth()
  );
  const rows = data?.results ?? [];
  return (
    <SectionCard
      subtitle="Cada pila se evalúa por separado contra el RPO declarado."
      title="Respaldos"
    >
      {error ? (
        <Alert role="alert" severity="error" sx={{ m: 2 }}>
          {error}
        </Alert>
      ) : null}
      <SectionTableArea>
        <DataTable
          columns={[
            {
              key: "stack",
              label: "Pila",
              render: (row) => BACKUP_STACK_LABEL[row.stack] ?? row.stack,
            },
            {
              key: "meets_rpo",
              label: "Estado",
              render: (row) =>
                row.meets_rpo ? (
                  <StatusChip label="Dentro del RPO" variant="success" />
                ) : (
                  <StatusChip label="Fuera del RPO" variant="danger" />
                ),
            },
            {
              key: "created_at",
              label: "Último respaldo",
              render: (row) =>
                row.created_at ? (
                  formatDateTime(row.created_at)
                ) : (
                  <MutedCell>Nunca</MutedCell>
                ),
            },
            {
              key: "age_hours",
              label: "Antigüedad",
              render: (row) =>
                row.age_hours == null
                  ? "—"
                  : `${row.age_hours.toLocaleString("es-GT", { maximumFractionDigits: 1 })} h (RPO ${row.rpo_hours} h)`,
            },
            {
              key: "size_bytes",
              label: "Tamaño",
              render: (row) => formatBytes(row.size_bytes),
            },
            { key: "backup_count", label: "Respaldos", align: "right" },
          ]}
          emptyMessage="Sin información de respaldos."
          getRowKey={(row) => row.stack}
          loading={loading}
          rows={rows}
        />
      </SectionTableArea>
    </SectionCard>
  );
}

function TaskHealth() {
  const { data, error, loading } = useResourceQuery(
    queryKeys.platform.taskHealth(),
    () => platformService.taskHealth()
  );
  return (
    <SectionCard
      subtitle="Una fila por tarea conocida: su última ejecución y cuántas fallaron."
      title="Tareas programadas"
    >
      {error ? (
        <Alert role="alert" severity="error" sx={{ m: 2 }}>
          {error}
        </Alert>
      ) : null}
      <SectionTableArea>
        <DataTable
          columns={[
            { key: "name", label: "Tarea" },
            {
              key: "last_status",
              label: "Último estado",
              render: (row) => <TaskStatus status={row.last_status} />,
            },
            {
              key: "last_started_at",
              label: "Última ejecución",
              render: (row) => formatDateTime(row.last_started_at),
            },
            {
              key: "last_duration_ms",
              label: "Duración",
              render: (row) => formatDuration(row.last_duration_ms),
            },
            { key: "total_runs", label: "Ejecuciones", align: "right" },
            { key: "failed_runs", label: "Fallidas", align: "right" },
            {
              key: "last_error_message",
              label: "Último error",
              render: (row) =>
                row.last_error_message || <MutedCell>—</MutedCell>,
            },
          ]}
          emptyMessage="Todavía no se registró ninguna ejecución."
          getRowKey={(row) => row.name}
          loading={loading}
          rows={data?.results ?? []}
        />
      </SectionTableArea>
    </SectionCard>
  );
}

function TaskRuns() {
  // El backend filtra por nombre exacto: se ofrecen los nombres conocidos.
  const { data: health } = useResourceQuery(
    queryKeys.platform.taskHealth(),
    () => platformService.taskHealth()
  );
  const nameOptions = (health?.results ?? []).map((task) => ({
    value: task.name,
    label: task.name,
  }));
  const list = useServerList({
    queryKey: [...queryKeys.platform.all, "task-runs"],
    fetchPage: platformService.taskRuns,
    defaultFilters: { name: "", status: "" },
    urlPrefix: "runs_",
  });
  return (
    <ListSection
      columns={[
        { key: "name", label: "Tarea" },
        {
          key: "status",
          label: "Estado",
          render: (row) => <TaskStatus status={row.status} />,
        },
        {
          key: "started_at",
          label: "Inicio",
          render: (row) => formatDateTime(row.started_at),
        },
        {
          key: "duration_ms",
          label: "Duración",
          render: (row) => formatDuration(row.duration_ms),
        },
        {
          key: "host",
          label: "Equipo",
          render: (row) => row.host || <MutedCell>—</MutedCell>,
        },
        {
          key: "error_message",
          label: "Error",
          render: (row) => row.error_message || <MutedCell>—</MutedCell>,
        },
      ]}
      emptyMessage="Sin ejecuciones para los filtros seleccionados."
      filters={
        <FilterBar>
          <FilterSelect
            emptyLabel="Todas las tareas"
            label="Tarea"
            minWidth={220}
            onChange={(value) => list.setFilter("name", value)}
            options={nameOptions}
            value={list.filters.name}
          />
          <FilterSelect
            emptyLabel="Todos los estados"
            label="Estado"
            onChange={(value) => list.setFilter("status", value)}
            options={TASK_STATUS_OPTIONS}
            value={list.filters.status}
          />
        </FilterBar>
      }
      getRowKey={(row) => row.public_id}
      list={list}
      showInactiveToggle={false}
      title="Historial de ejecuciones"
    />
  );
}

/**
 * Plataforma (docs/ux-ui.md AU3): salud del servicio, de las tareas
 * programadas y de los respaldos. Solo lectura: las ejecuciones son historia.
 */
export function PlatformPage() {
  return (
    <>
      <PageHeader
        breadcrumb="Administración"
        subtitle="Estado del servicio, de las tareas programadas y de los respaldos."
        title="Plataforma"
      />
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <ServiceHealth />
        </Grid>
        <Grid size={{ xs: 12, md: 8 }}>
          <BackupHealth />
        </Grid>
      </Grid>
      <TaskHealth />
      <TaskRuns />
    </>
  );
}
