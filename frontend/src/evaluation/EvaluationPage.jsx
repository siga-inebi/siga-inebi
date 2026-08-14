import { useCallback, useEffect, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import EventRepeatOutlinedIcon from "@mui/icons-material/EventRepeatOutlined";
import KeyOutlinedIcon from "@mui/icons-material/KeyOutlined";

import { PAGE_SIZE } from "@academics/academicsService.js";
import { cyclesService } from "@cycles/cyclesService.js";
import { evaluationService } from "@evaluation/evaluationService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDate } from "@shared/utils/format.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { StatCard } from "@ui/display/StatCard.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { EmptyState } from "@ui/feedback/EmptyState.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";

import { CaptureExceptionsWindow } from "./CaptureExceptionsWindow.jsx";

const UNIT_COLUMNS = [
  { key: "number", label: "N.", align: "right", render: (row) => row.number },
  { key: "name", label: "Unidad", render: (row) => row.name },
  {
    key: "period",
    label: "Periodo",
    render: (row) =>
      `${formatDate(row.starts_on)} — ${formatDate(row.ends_on)}`,
  },
  {
    key: "capture",
    label: "Captura",
    render: (row) =>
      `${formatDate(row.capture_starts_on)} — ${formatDate(row.capture_ends_on)}`,
  },
  {
    key: "recovery",
    label: "Recuperacion",
    render: (row) =>
      `${formatDate(row.recovery_starts_on)} — ${formatDate(row.recovery_ends_on)}`,
  },
  {
    key: "status",
    label: "Estado",
    render: (row) =>
      row.status ? <StatusChip label={row.status} variant="primary" /> : null,
  },
];

const UNIT_FIELDS = [
  {
    name: "number",
    label: "Numero de unidad",
    type: "number",
    min: 1,
    required: true,
  },
  {
    name: "name",
    label: "Nombre",
    required: true,
    placeholder: "Ejemplo: Primer bimestre",
  },
  {
    name: "starts_on",
    label: "Inicio del periodo",
    type: "date",
    required: true,
  },
  { name: "ends_on", label: "Fin del periodo", type: "date", required: true },
  {
    name: "capture_starts_on",
    label: "Captura desde",
    type: "date",
    required: true,
  },
  {
    name: "capture_ends_on",
    label: "Captura hasta",
    type: "date",
    required: true,
  },
  {
    name: "recovery_starts_on",
    label: "Recuperacion desde",
    type: "date",
    required: true,
  },
  {
    name: "recovery_ends_on",
    label: "Recuperacion hasta",
    type: "date",
    required: true,
  },
];

const RECOVERY_FIELDS = [
  {
    name: "recovery_starts_on",
    label: "Recuperacion desde",
    type: "date",
    required: true,
  },
  {
    name: "recovery_ends_on",
    label: "Recuperacion hasta",
    type: "date",
    required: true,
  },
];

const UNIT_COUNT_FIELDS = [
  {
    name: "unit_count",
    label: "Unidades de evaluacion del ciclo",
    type: "number",
    min: 1,
    required: true,
    help: "Sobrescribe el default institucional solo para este ciclo.",
  },
];

const GLOBAL_COUNT_FIELDS = [
  {
    name: "default_unit_count",
    label: "Unidades por defecto",
    type: "number",
    min: 1,
    required: true,
    help: "Valor que hereda cada ciclo nuevo mientras no configure el suyo.",
  },
];

/**
 * Configuracion de evaluacion: default institucional, override por ciclo y
 * unidades de evaluacion con sus ventanas de captura y recuperacion.
 *
 * Todo cuelga del ciclo seleccionado porque asi lo modela el backend: las
 * unidades viven bajo `/cycles/{id}/evaluation-units/`. Sin ciclo elegido no hay
 * nada que listar, y la pantalla lo dice en vez de mostrar una tabla vacia.
 */
export function EvaluationPage() {
  const [cycles, setCycles] = useState([]);
  const [cycleId, setCycleId] = useState("");
  const [globalConfig, setGlobalConfig] = useState(null);
  const [cycleConfig, setCycleConfig] = useState(null);
  const [configError, setConfigError] = useState("");
  const [editing, setEditing] = useState(null);
  const [exceptionsFor, setExceptionsFor] = useState(null);

  // El selector de ciclo se llena una vez y preselecciona el vigente: es el que
  // el usuario quiere ver el 95% de las veces.
  useEffect(() => {
    let active = true;
    cyclesService
      .list()
      .then((page) => {
        if (!active) return;
        const items = page?.results ?? [];
        setCycles(items);
        const preferred =
          items.find((cycle) => cycle.status === "active") ?? items[0];
        if (preferred) setCycleId(preferred.public_id);
      })
      .catch((requestError) => {
        if (active) setConfigError(requestError.message);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;
    evaluationService
      .getGlobalConfig()
      .then((data) => {
        if (active) setGlobalConfig(data);
      })
      .catch((requestError) => {
        if (active) setConfigError(requestError.message);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!cycleId) return undefined;
    let active = true;
    evaluationService
      .getCycleConfig(cycleId)
      .then((data) => {
        if (active) setCycleConfig(data);
      })
      .catch(() => {
        // Un ciclo sin configuracion propia es normal: hereda la global.
        if (active) setCycleConfig(null);
      });
    return () => {
      active = false;
    };
  }, [cycleId, editing]);

  const loadUnits = useCallback(
    (params) => evaluationService.listUnits(cycleId, params),
    [cycleId]
  );
  const list = usePaginatedList(cycleId ? loadUnits : EMPTY_LOADER, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  const cycleOptions = cycles.map((cycle) => ({
    value: cycle.public_id,
    label: `${cycle.name} (${cycle.year})`,
  }));

  const handleCreateUnit = async (payload) => {
    await evaluationService.createUnit(cycleId, payload);
    setEditing(null);
    list.refresh();
  };

  const handleRecovery = async (payload) => {
    await evaluationService.updateRecoveryWindow(
      cycleId,
      editing.unit.public_id,
      payload
    );
    setEditing(null);
    list.refresh();
  };

  const handleGlobalConfig = async (payload) => {
    const updated = await evaluationService.updateGlobalConfig(payload);
    setGlobalConfig(updated);
    setEditing(null);
  };

  const handleCycleConfig = async (payload) => {
    const updated = await evaluationService.updateCycleConfig(cycleId, payload);
    setCycleConfig(updated);
    setEditing(null);
  };

  return (
    <>
      <PageHeader
        action={
          <Button
            disabled={!cycleId}
            onClick={() => setEditing({ mode: "unit" })}
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nueva unidad
          </Button>
        }
        breadcrumb="Evaluacion"
        subtitle="Unidades de evaluacion del ciclo con sus ventanas de captura y recuperacion, y el numero de unidades configurado."
        title="Configuracion de evaluacion"
      />

      {configError ? <Alert severity="error">{configError}</Alert> : null}

      <Grid container spacing={2} sx={{ mb: 1 }}>
        <Grid size={{ xs: 12, sm: 6 }}>
          <StatCard
            action={
              <Button
                onClick={() => setEditing({ mode: "globalConfig" })}
                size="small"
                variant="text"
              >
                Cambiar
              </Button>
            }
            hint="Default institucional que heredan los ciclos nuevos"
            label="Unidades por defecto"
            loading={globalConfig == null}
            value={globalConfig?.default_unit_count ?? "—"}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6 }}>
          <StatCard
            action={
              <Button
                disabled={!cycleId}
                onClick={() => setEditing({ mode: "cycleConfig" })}
                size="small"
                variant="text"
              >
                Cambiar
              </Button>
            }
            hint={
              cycleConfig
                ? "Configuracion propia de este ciclo"
                : "Este ciclo hereda el default institucional"
            }
            label="Unidades de este ciclo"
            value={
              cycleConfig?.unit_count ?? globalConfig?.default_unit_count ?? "—"
            }
          />
        </Grid>
      </Grid>

      <SectionCard
        fillHeight
        subtitle="Del ciclo seleccionado"
        title="Unidades de evaluacion"
      >
        <FilterBar>
          <FilterSelect
            label="Ciclo escolar"
            minWidth={260}
            onChange={setCycleId}
            options={cycleOptions}
            value={cycleId}
          />
          {cycleId ? null : (
            <Typography color="text.secondary" variant="body2">
              Elige un ciclo para ver sus unidades.
            </Typography>
          )}
        </FilterBar>

        {cycleId ? (
          <SectionTableArea>
            <DataTable
              columns={[
                ...UNIT_COLUMNS,
                {
                  key: "acciones",
                  label: "Acciones",
                  align: "right",
                  render: (unit) => (
                    <Stack direction="row" gap={0.5} justifyContent="flex-end">
                      <ActionIconButton
                        label="Ajustar ventana de recuperacion"
                        onClick={() => setEditing({ mode: "recovery", unit })}
                      >
                        <EventRepeatOutlinedIcon fontSize="small" />
                      </ActionIconButton>
                      <ActionIconButton
                        label="Permisos excepcionales de captura"
                        onClick={() => setExceptionsFor(unit)}
                      >
                        <KeyOutlinedIcon fontSize="small" />
                      </ActionIconButton>
                    </Stack>
                  ),
                },
              ]}
              emptyMessage="Este ciclo todavia no tiene unidades de evaluacion."
              fillHeight
              getRowKey={(row) => row.public_id}
              loading={list.loading}
              pagination={list.pagination}
              rows={list.items}
            />
          </SectionTableArea>
        ) : (
          <EmptyState message="Selecciona un ciclo escolar para ver y configurar sus unidades de evaluacion." />
        )}
      </SectionCard>

      {editing?.mode === "unit" ? (
        <EntityFormWindow
          description="Las tres ventanas son distintas: el periodo es cuando se imparte, la captura cuando el docente ingresa notas, y la recuperacion cuando puede corregirlas."
          fields={UNIT_FIELDS}
          initialValues={{
            number: list.count + 1,
            name: "",
            starts_on: "",
            ends_on: "",
            capture_starts_on: "",
            capture_ends_on: "",
            recovery_starts_on: "",
            recovery_ends_on: "",
          }}
          key="unit-create"
          onCancel={() => setEditing(null)}
          onSubmit={handleCreateUnit}
          open
          submitLabel="Crear unidad"
          title="Nueva unidad de evaluacion"
        />
      ) : null}

      {editing?.mode === "recovery" ? (
        <EntityFormWindow
          description={`Ventana de recuperacion de "${editing.unit.name}". La fecha de fin no puede ser anterior a la de inicio.`}
          fields={RECOVERY_FIELDS}
          initialValues={{
            recovery_starts_on: editing.unit.recovery_starts_on ?? "",
            recovery_ends_on: editing.unit.recovery_ends_on ?? "",
          }}
          key={`recovery-${editing.unit.public_id}`}
          onCancel={() => setEditing(null)}
          onSubmit={handleRecovery}
          open
          submitLabel="Guardar ventana"
          title="Ventana de recuperacion"
        />
      ) : null}

      {editing?.mode === "globalConfig" ? (
        <EntityFormWindow
          description="Este valor solo afecta a los ciclos que no tengan configuracion propia."
          fields={GLOBAL_COUNT_FIELDS}
          initialValues={{
            default_unit_count: globalConfig?.default_unit_count ?? 4,
          }}
          key="global-config"
          onCancel={() => setEditing(null)}
          onSubmit={handleGlobalConfig}
          open
          submitLabel="Guardar default"
          title="Configuracion institucional de evaluacion"
        />
      ) : null}

      {editing?.mode === "cycleConfig" ? (
        <EntityFormWindow
          description="Configuracion propia de este ciclo. Deja de heredar el default institucional."
          fields={UNIT_COUNT_FIELDS}
          initialValues={{
            unit_count:
              cycleConfig?.unit_count ?? globalConfig?.default_unit_count ?? 4,
          }}
          key="cycle-config"
          onCancel={() => setEditing(null)}
          onSubmit={handleCycleConfig}
          open
          submitLabel="Guardar configuracion"
          title="Configuracion del ciclo"
        />
      ) : null}

      {exceptionsFor ? (
        <CaptureExceptionsWindow
          cycleId={cycleId}
          key={exceptionsFor.public_id}
          onClose={() => setExceptionsFor(null)}
          unit={exceptionsFor}
        />
      ) : null}
    </>
  );
}

/** Cargador inerte mientras no hay ciclo elegido (ver `EnrolmentsPage`). */
const EMPTY_LOADER = () => Promise.resolve({ count: 0, results: [] });
