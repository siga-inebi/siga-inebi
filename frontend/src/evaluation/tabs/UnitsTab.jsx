import { lazy, Suspense, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";

import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import {
  evaluationService,
  UNIT_STATUS_LABEL,
  UNIT_STATUS_VARIANT,
} from "@evaluation/evaluationService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { formatDate } from "@shared/utils/format.js";
import { RowActionsMenu } from "@ui/buttons/RowActionsMenu.jsx";
import { StatCard } from "@ui/display/StatCard.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";

const CaptureExceptionsWindow = lazy(() =>
  import("../CaptureExceptionsWindow.jsx").then((m) => ({
    default: m.CaptureExceptionsWindow,
  }))
);
const CloneConfigWindow = lazy(() =>
  import("../CloneConfigWindow.jsx").then((m) => ({
    default: m.CloneConfigWindow,
  }))
);

const range = (from, to) =>
  from || to ? `${formatDate(from)} — ${formatDate(to)}` : "Sin ventana";

const UNIT_COLUMNS = [
  { key: "number", label: "N.º", align: "right", render: (row) => row.number },
  { key: "name", label: "Unidad", render: (row) => row.name },
  {
    key: "period",
    label: "Período",
    render: (row) => range(row.starts_on, row.ends_on),
  },
  {
    key: "capture",
    label: "Captura",
    render: (row) => range(row.capture_starts_on, row.capture_ends_on),
  },
  {
    key: "recovery",
    label: "Recuperación",
    render: (row) => range(row.recovery_starts_on, row.recovery_ends_on),
  },
  {
    key: "status",
    label: "Estado",
    render: (row) => (
      <StatusChip
        label={UNIT_STATUS_LABEL[row.status] ?? row.status}
        variant={UNIT_STATUS_VARIANT[row.status] ?? "neutral"}
      />
    ),
  },
];

const date = (name, label, required = true) => ({
  name,
  label,
  type: "date",
  required,
});

const RECOVERY_FIELDS = [
  date("recovery_starts_on", "Recuperación desde"),
  date("recovery_ends_on", "Recuperación hasta"),
];

const UNIT_FIELDS = [
  {
    name: "number",
    label: "Número de unidad",
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
  date("starts_on", "Inicio del período"),
  date("ends_on", "Fin del período"),
  date("capture_starts_on", "Captura desde"),
  date("capture_ends_on", "Captura hasta"),
  date("recovery_starts_on", "Recuperación desde (opcional)", false),
  date("recovery_ends_on", "Recuperación hasta (opcional)", false),
];

/**
 * La ventana de recuperación es opcional al crear, pero va completa: las dos
 * fechas o ninguna (el backend rechaza una sola). Se avisa antes de enviar.
 */
function unitPayload(values) {
  const { recovery_starts_on: from, recovery_ends_on: to, ...rest } = values;
  if (Boolean(from) !== Boolean(to)) {
    throw new Error(
      "Escriba las dos fechas de la ventana de recuperación, o deje ambas vacías."
    );
  }
  return from
    ? { ...rest, recovery_starts_on: from, recovery_ends_on: to }
    : rest;
}

/**
 * Unidades y configuración de evaluación del ciclo (RF-EVC-*): número de
 * unidades (default institucional y del ciclo), unidades con sus ventanas,
 * cierre de unidad (V1), permisos excepcionales y clonado a otro ciclo (V6).
 */
export function UnitsTab({ cycle, cycles, goTo }) {
  const cycleId = cycle.public_id;
  const { can } = usePermissions();
  const canConfigure = can(PERMISSION.EVALUATION_CONFIGURE_UNITS);
  const canOpenSheet = can([
    PERMISSION.GRADE_WRITE,
    PERMISSION.EVALUATION_CONFIGURE_UNITS,
  ]);
  const isClosed = cycle.status === "closed";

  const [editing, setEditing] = useState(null);
  const [closing, setClosing] = useState(null);
  const [closeBusy, setCloseBusy] = useState(false);
  const [closeError, setCloseError] = useState("");

  const globalConfig = useQuery({
    queryKey: queryKeys.evaluation("", "config"),
    queryFn: () => evaluationService.getGlobalConfig(),
  });
  const cycleConfig = useQuery({
    queryKey: queryKeys.evaluation(cycleId, "config"),
    // Un ciclo sin configuración propia es normal: hereda la global.
    queryFn: () => evaluationService.getCycleConfig(cycleId).catch(() => null),
  });
  const globalCount = globalConfig.data?.default_unit_count;
  const cycleCount = cycleConfig.data?.unit_count;

  const list = useServerList({
    queryKey: queryKeys.evaluation(cycleId, "unit-list"),
    fetchPage: (params) => evaluationService.listUnits(cycleId, params),
    urlPrefix: "u_",
  });

  const save = async (request) => {
    await request;
    setEditing(null);
  };

  const confirmClose = async () => {
    setCloseBusy(true);
    setCloseError("");
    try {
      await evaluationService.closeUnit(cycleId, closing.public_id);
      setClosing(null);
      list.refresh();
    } catch (requestError) {
      setCloseError(requestError.message);
    } finally {
      setCloseBusy(false);
    }
  };

  return (
    <Stack gap={2}>
      {globalConfig.error ? (
        <Alert severity="error">{globalConfig.error.message}</Alert>
      ) : null}
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 6 }}>
          <StatCard
            action={
              canConfigure ? (
                <Button
                  aria-label="Cambiar unidades por defecto"
                  onClick={() => setEditing({ mode: "global" })}
                  size="small"
                >
                  Cambiar
                </Button>
              ) : null
            }
            hint="Default institucional que heredan los ciclos nuevos"
            label="Unidades por defecto"
            loading={globalConfig.isPending}
            value={globalCount ?? "—"}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6 }}>
          <StatCard
            action={
              canConfigure ? (
                <Button
                  aria-label="Cambiar unidades de este ciclo"
                  onClick={() => setEditing({ mode: "cycle" })}
                  size="small"
                >
                  Cambiar
                </Button>
              ) : null
            }
            hint={
              cycleConfig.data
                ? "Configuración propia de este ciclo"
                : "Este ciclo hereda el default institucional"
            }
            label="Unidades de este ciclo"
            value={cycleCount ?? globalCount ?? "—"}
          />
        </Grid>
      </Grid>

      <ListSection
        action={
          canConfigure ? (
            <Stack direction="row" flexWrap="wrap" gap={1}>
              <Button
                onClick={() => setEditing({ mode: "clone" })}
                size="small"
                variant="outlined"
              >
                Clonar configuración a otro ciclo
              </Button>
              <Button
                disabled={isClosed}
                onClick={() => setEditing({ mode: "unit" })}
                size="small"
                variant="contained"
              >
                Nueva unidad
              </Button>
            </Stack>
          ) : null
        }
        columns={UNIT_COLUMNS}
        emptyMessage="Este ciclo todavía no tiene unidades de evaluación."
        getRowKey={(row) => row.public_id}
        list={list}
        renderActions={(unit) => (
          <RowActionsMenu
            actions={[
              {
                key: "sheet",
                label: "Abrir planilla",
                hidden: !canOpenSheet,
                onClick: () => goTo("planilla", { unidad: unit.public_id }),
              },
              {
                key: "progress",
                label: "Ver avance de captura",
                hidden: !canOpenSheet,
                onClick: () => goTo("avance", { unidad: unit.public_id }),
              },
              {
                key: "recovery",
                label: "Ajustar ventana de recuperación",
                hidden: !canConfigure,
                onClick: () => setEditing({ mode: "recovery", unit }),
              },
              {
                key: "exceptions",
                label: "Permisos excepcionales de captura",
                hidden: !canConfigure,
                onClick: () => setEditing({ mode: "exceptions", unit }),
              },
              {
                key: "close",
                label: "Cerrar unidad",
                danger: true,
                hidden: !canConfigure || unit.status === "closed",
                onClick: () => {
                  setCloseError("");
                  setClosing(unit);
                },
              },
            ]}
            label={unit.name}
          />
        )}
        showInactiveToggle={false}
        subtitle="Cada unidad tiene su período, su ventana de captura de notas y, si aplica, su ventana de recuperación."
        title="Unidades de evaluación"
      />

      <ConfirmDialog
        busy={closeBusy}
        confirmColor="error"
        confirmText="Cerrar unidad"
        errorText={closeError || undefined}
        message={
          closing
            ? `Al cerrar «${closing.name}» ya no se pueden registrar ni corregir sus notas. Cerrar todas las unidades es requisito para cerrar el ciclo escolar. Queda registrado en la bitácora.`
            : ""
        }
        onClose={() => {
          if (!closeBusy) setClosing(null);
        }}
        onConfirm={confirmClose}
        open={Boolean(closing)}
        title="Cerrar unidad de evaluación"
      />

      {editing?.mode === "unit" ? (
        <EntityFormWindow
          description="El período es cuando se imparte la unidad, la captura cuando el docente registra notas y la recuperación, si se define ahora, cuando se registran las notas de recuperación."
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
          onCancel={() => setEditing(null)}
          onSubmit={(values) =>
            save(evaluationService.createUnit(cycleId, unitPayload(values)))
          }
          open
          submitLabel="Crear unidad"
          title="Nueva unidad de evaluación"
        />
      ) : null}

      {editing?.mode === "recovery" ? (
        <EntityFormWindow
          description={`Ventana de recuperación de «${editing.unit.name}». La fecha de fin no puede ser anterior a la de inicio.`}
          fields={RECOVERY_FIELDS}
          initialValues={{
            recovery_starts_on: editing.unit.recovery_starts_on ?? "",
            recovery_ends_on: editing.unit.recovery_ends_on ?? "",
          }}
          onCancel={() => setEditing(null)}
          onSubmit={(values) =>
            save(
              evaluationService.updateRecoveryWindow(
                cycleId,
                editing.unit.public_id,
                values
              )
            )
          }
          open
          submitLabel="Guardar ventana"
          title="Ventana de recuperación"
        />
      ) : null}

      {editing?.mode === "global" ? (
        <EntityFormWindow
          description="Este valor solo afecta a los ciclos que no tengan configuración propia."
          fields={[
            {
              name: "default_unit_count",
              label: "Unidades por defecto",
              type: "number",
              min: 1,
              required: true,
            },
          ]}
          initialValues={{ default_unit_count: globalCount ?? 4 }}
          onCancel={() => setEditing(null)}
          onSubmit={(values) =>
            save(evaluationService.updateGlobalConfig(values))
          }
          open
          submitLabel="Guardar default"
          title="Configuración institucional de evaluación"
        />
      ) : null}

      {editing?.mode === "cycle" ? (
        <EntityFormWindow
          description="Configuración propia de este ciclo: deja de heredar el default institucional."
          fields={[
            {
              name: "unit_count",
              label: "Unidades de evaluación del ciclo",
              type: "number",
              min: 1,
              required: true,
            },
          ]}
          initialValues={{ unit_count: cycleCount ?? globalCount ?? 4 }}
          onCancel={() => setEditing(null)}
          onSubmit={(values) =>
            save(evaluationService.updateCycleConfig(cycleId, values))
          }
          open
          submitLabel="Guardar configuración"
          title="Configuración de evaluación del ciclo"
        />
      ) : null}

      <Suspense fallback={null}>
        {editing?.mode === "exceptions" ? (
          <CaptureExceptionsWindow
            cycleId={cycleId}
            onClose={() => setEditing(null)}
            unit={editing.unit}
          />
        ) : null}
        {editing?.mode === "clone" ? (
          <CloneConfigWindow
            cycle={cycle}
            cycles={cycles}
            onClose={() => setEditing(null)}
          />
        ) : null}
      </Suspense>
    </Stack>
  );
}
