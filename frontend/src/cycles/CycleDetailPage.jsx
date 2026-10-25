import { lazy, Suspense, useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";

import {
  CYCLE_STATUS,
  CYCLE_STATUS_LABEL,
  CYCLE_STATUS_VARIANT,
  cyclesService,
} from "@cycles/cyclesService.js";
import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { formatDate } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { TextLink } from "@ui/display/TextLink.jsx";
import { DetailField } from "@ui/layout/DetailWindow.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";

import { CycleHistory } from "./CycleHistory.jsx";
import { cyclePath } from "./cyclePresentation.js";
import { useCycleActions } from "./useCycleActions.jsx";

const SectionsTab = lazy(() =>
  import("./tabs/SectionsTab.jsx").then((m) => ({ default: m.SectionsTab }))
);
const CurriculumPlanTab = lazy(() =>
  import("./tabs/CurriculumPlanTab.jsx").then((m) => ({
    default: m.CurriculumPlanTab,
  }))
);
const AssignmentMatrixTab = lazy(() =>
  import("./tabs/AssignmentMatrixTab.jsx").then((m) => ({
    default: m.AssignmentMatrixTab,
  }))
);
const ScheduleTab = lazy(() =>
  import("./tabs/ScheduleTab.jsx").then((m) => ({ default: m.ScheduleTab }))
);
const NonComputableDaysTab = lazy(() =>
  import("./tabs/NonComputableDaysTab.jsx").then((m) => ({
    default: m.NonComputableDaysTab,
  }))
);
const CYCLE_TABS = [
  ["resumen", "Resumen"],
  ["pendientes", "Pendientes"],
  ["secciones", "Secciones"],
  ["plan", "Plan de estudios"],
  ["asignaciones", "Asignaciones"],
  ["horarios", "Horarios"],
  ["dias", "Días no computables"],
];

/** Pestaña que resuelve cada faltante de activación (C7), y su filtro. */
function gapTarget(gap) {
  switch (gap.code) {
    case "no_grade_offerings":
    case "missing_sections":
      return { tab: "secciones", label: "Ir a Secciones" };
    case "missing_curriculum_plan":
      return {
        tab: "plan",
        label: "Ir a Plan de estudios",
        params: gap.grade ? { plan_grade_id: gap.grade.public_id } : {},
      };
    case "missing_teacher":
      return {
        tab: "asignaciones",
        label: "Ir a Asignaciones",
        params: gap.grade ? { mat_grade_id: gap.grade.public_id } : {},
      };
    default:
      return null;
  }
}

/** Botones de acción con su motivo en un tooltip cuando no proceden. */
function LifecycleButtons({ actions }) {
  const visible = actions.filter(
    (action) => !action.hidden && action.key !== "view"
  );
  if (visible.length === 0) return null;
  return (
    <Stack direction="row" flexWrap="wrap" gap={1}>
      {visible.map((action) => (
        <Tooltip key={action.key} title={action.disabled ? action.hint : ""}>
          <span>
            <Button
              color={action.key === "close" ? "error" : "primary"}
              disabled={action.disabled}
              onClick={action.onClick}
              size="small"
              variant={action.key === "activate" ? "contained" : "outlined"}
            >
              {action.label}
            </Button>
          </span>
        </Tooltip>
      ))}
    </Stack>
  );
}

function Checklist({ items, title }) {
  return (
    <Box>
      <Typography sx={{ fontWeight: 600, mb: 0.5 }} variant="body2">
        {title}
      </Typography>
      <List dense disablePadding>
        {items.map((item, index) => (
          <ListItem
            disableGutters
            key={`${item.key}-${index}`}
            secondaryAction={item.action}
            sx={{ pr: item.action ? 18 : 0 }}
          >
            <ListItemText primary={item.message} />
          </ListItem>
        ))}
      </List>
    </Box>
  );
}

function PendingTab({ cycle, goTo, readiness }) {
  const isDraft = cycle.status === CYCLE_STATUS.draft;
  const isActive = cycle.status === CYCLE_STATUS.active;
  const activeCycle = readiness?.active_cycle;
  const activationGaps = (readiness?.activation?.gaps ?? []).filter(
    (gap) => gap.code !== "invalid_status"
  );
  const closeGaps = (readiness?.close?.gaps ?? []).filter(
    (gap) => gap.code !== "invalid_status"
  );
  const revertBlockers = (readiness?.revert?.blockers ?? []).filter(
    (blocker) => blocker.code !== "invalid_status"
  );

  return (
    <Stack gap={3}>
      {isDraft && activeCycle ? (
        <Alert severity="info">
          Para activar este ciclo, cierre primero el ciclo «{activeCycle.name}
          ».{" "}
          <TextLink to={cyclePath(activeCycle)}>
            Ver «{activeCycle.name}»
          </TextLink>
        </Alert>
      ) : null}

      {isDraft && readiness ? (
        activationGaps.length === 0 ? (
          <Alert severity="success">
            La estructura está completa: el ciclo se puede activar.
          </Alert>
        ) : (
          <Checklist
            items={activationGaps.map((gap) => {
              const target = gapTarget(gap);
              return {
                key: gap.code,
                message: gap.message,
                action:
                  gap.code === "active_cycle_exists" && activeCycle ? (
                    <Button
                      component={Link}
                      size="small"
                      to={cyclePath(activeCycle)}
                    >
                      Ver ciclo activo
                    </Button>
                  ) : target ? (
                    <Button
                      onClick={() => goTo(target.tab, target.params)}
                      size="small"
                    >
                      {target.label}
                    </Button>
                  ) : null,
              };
            })}
            title={`Falta para activar (${activationGaps.length})`}
          />
        )
      ) : null}

      {isActive && readiness ? (
        <>
          {closeGaps.length > 0 ? (
            <Checklist
              items={closeGaps.map((gap) => ({
                key: gap.code,
                message: gap.message,
                action: (
                  <Button component={Link} size="small" to="/app/evaluacion">
                    Ir a Evaluación
                  </Button>
                ),
              }))}
              title={`Pendiente para cerrar (${closeGaps.length})`}
            />
          ) : (
            <Alert severity="success">
              No hay pendientes: el ciclo se puede cerrar.
            </Alert>
          )}
          {revertBlockers.length > 0 ? (
            <Checklist
              items={revertBlockers.map((blocker) => ({
                key: blocker.code,
                message: blocker.message,
              }))}
              title="Por qué ya no puede volver a borrador"
            />
          ) : null}
        </>
      ) : null}
    </Stack>
  );
}

function SummaryTab({ actions, cycle, detail }) {
  return (
    <Stack gap={3}>
      <Box
        component="dl"
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "repeat(4, 1fr)" },
          gap: 2.5,
          m: 0,
        }}
      >
        <DetailField label="Año" value={cycle.year} />
        <DetailField
          label="Vigencia"
          value={`${formatDate(cycle.starts_on)} — ${formatDate(cycle.ends_on)}`}
        />
        <DetailField
          label="Estado"
          value={
            <StatusChip
              label={CYCLE_STATUS_LABEL[cycle.status] ?? cycle.status}
              variant={CYCLE_STATUS_VARIANT[cycle.status] ?? "neutral"}
            />
          }
        />
        <DetailField
          label="Descripción"
          value={cycle.description || "Sin descripción"}
        />
      </Box>

      <LifecycleButtons actions={actions} />

      <SectionCard
        subtitle="Lo que quedó registrado en el ciclo. Solo consulta."
        title="Estructura registrada"
      >
        <Box sx={{ p: { xs: 2, md: 2.5 } }}>
          <CycleHistory detail={detail} />
        </Box>
      </SectionCard>
    </Stack>
  );
}

function CycleDetail({ cycleId }) {
  const { can } = usePermissions();
  const [params, setParams] = useSearchParams();
  const current = CYCLE_TABS.some(([id]) => id === params.get("tab"))
    ? params.get("tab")
    : "resumen";
  const [visited, setVisited] = useState([current]);
  useEffect(() => {
    setVisited((list) => (list.includes(current) ? list : [...list, current]));
  }, [current]);

  const detail = useQuery({
    queryKey: queryKeys.academics.cycleDetail(cycleId),
    queryFn: () => cyclesService.get(cycleId),
  });
  const readiness = useQuery({
    queryKey: queryKeys.academics.readiness(cycleId),
    queryFn: () => cyclesService.readiness(cycleId),
  });

  const refresh = () => {
    detail.refetch();
    readiness.refetch();
  };
  const { actionsFor, dialogs } = useCycleActions({ onChanged: refresh });

  const goTo = (next, extra = {}) =>
    setParams((existing) => {
      const updated = new URLSearchParams(existing);
      updated.set("tab", next);
      for (const [key, value] of Object.entries(extra)) {
        updated.set(key, value);
      }
      return updated;
    });

  const cycle = detail.data;
  const canManage = can(PERMISSION.SCOPE_ASSIGN);

  return (
    <>
      <PageHeader
        action={
          <Button component={Link} to="/app/ciclos">
            Volver a ciclos
          </Button>
        }
        breadcrumb="Estructura académica · Ciclo escolar"
        subtitle={
          cycle
            ? `${CYCLE_STATUS_LABEL[cycle.status] ?? cycle.status} · ${formatDate(cycle.starts_on)} — ${formatDate(cycle.ends_on)}`
            : "Preparación y consulta del ciclo"
        }
        title={cycle?.name ?? "Ciclo escolar"}
      />
      {dialogs}
      {detail.error ? (
        <Alert
          action={
            <Button color="inherit" onClick={() => detail.refetch()}>
              Reintentar
            </Button>
          }
          severity="error"
        >
          {detail.error.message}
        </Alert>
      ) : !cycle ? (
        <Typography role="status">Cargando ciclo…</Typography>
      ) : (
        <SectionCard sx={{ p: { xs: 2, sm: 3 } }}>
          <Stack gap={2}>
            <Tabs
              allowScrollButtonsMobile
              aria-label="Partes del ciclo"
              onChange={(_event, next) => goTo(next)}
              scrollButtons="auto"
              value={current}
              variant="scrollable"
            >
              {CYCLE_TABS.map(([id, label]) => (
                <Tab
                  aria-controls={`cycle-panel-${id}`}
                  id={`cycle-tab-${id}`}
                  key={id}
                  label={label}
                  value={id}
                />
              ))}
            </Tabs>
            <Suspense
              fallback={
                <Typography role="status">Cargando sección…</Typography>
              }
            >
              {[...new Set([...visited, current])].map((id) => (
                <Box
                  aria-labelledby={`cycle-tab-${id}`}
                  hidden={id !== current}
                  id={`cycle-panel-${id}`}
                  key={id}
                  role="tabpanel"
                >
                  {id === "resumen" ? (
                    <SummaryTab
                      actions={actionsFor(cycle, {
                        activeCycle: readiness.data?.active_cycle ?? null,
                        readiness: readiness.data ?? null,
                      })}
                      cycle={cycle}
                      detail={cycle}
                    />
                  ) : id === "pendientes" ? (
                    <PendingTab
                      cycle={cycle}
                      goTo={goTo}
                      readiness={readiness.data}
                    />
                  ) : id === "secciones" ? (
                    <SectionsTab canManage={canManage} cycle={cycle} />
                  ) : id === "plan" ? (
                    <CurriculumPlanTab canManage={canManage} cycle={cycle} />
                  ) : id === "asignaciones" ? (
                    <AssignmentMatrixTab canManage={canManage} cycle={cycle} />
                  ) : id === "horarios" ? (
                    <ScheduleTab canManage={canManage} cycle={cycle} />
                  ) : (
                    <NonComputableDaysTab canManage={canManage} cycle={cycle} />
                  )}
                </Box>
              ))}
            </Suspense>
          </Stack>
        </SectionCard>
      )}
    </>
  );
}

/**
 * Detalle del ciclo escolar (docs/ux-ui.md C9, 1.5): reemplaza la ventana del
 * detalle histórico por una ruta con pestañas (`?tab=`). En un borrador es el
 * tablero de preparación con la lista de verificación de activación (C7); en
 * un ciclo activo o cerrado, la consulta de su estructura.
 */
export function CycleDetailPage() {
  const { cycleId } = useParams();
  return <CycleDetail cycleId={cycleId} key={cycleId} />;
}
