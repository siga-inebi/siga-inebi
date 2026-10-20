import { lazy, Suspense, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";

import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { CYCLE_STATUS_LABEL, cyclesService } from "@cycles/cyclesService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { EmptyState } from "@ui/feedback/EmptyState.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";

const named = (load, name) =>
  lazy(() => load().then((m) => ({ default: m[name] })));

// Cada pestaña es un chunk aparte: la ruta solo descarga la que se abre.
const UnitsTab = named(() => import("./tabs/UnitsTab.jsx"), "UnitsTab");
const GradeSheetTab = named(
  () => import("./tabs/GradeSheetTab.jsx"),
  "GradeSheetTab"
);
const CaptureProgressTab = named(
  () => import("./tabs/CaptureProgressTab.jsx"),
  "CaptureProgressTab"
);
const RecoveryTab = named(
  () => import("./tabs/RecoveryTab.jsx"),
  "RecoveryTab"
);
const ResultsTab = named(() => import("./tabs/ResultsTab.jsx"), "ResultsTab");

const {
  EVALUATION_CONFIGURE_UNITS,
  GRADE_WRITE,
  GRADE_CORRECT,
  STUDENT_VIEW_BASIC,
} = PERMISSION;

/** Pestañas y el permiso que basta para verlas (vacío: solo sesión). */
const TABS = [
  ["unidades", "Unidades", []],
  ["planilla", "Planilla", [GRADE_WRITE, EVALUATION_CONFIGURE_UNITS]],
  ["avance", "Avance", [GRADE_WRITE, EVALUATION_CONFIGURE_UNITS]],
  ["recuperacion", "Recuperación", [STUDENT_VIEW_BASIC]],
  ["resultados", "Resultados", [STUDENT_VIEW_BASIC, GRADE_CORRECT]],
];

/** Parámetros propios de un ciclo: se quitan al cambiar de ciclo. */
const CYCLE_SCOPED = ["unidad", "seccion", "subarea", "estudiante"];

function TabPanel({ id, ...props }) {
  switch (id) {
    case "planilla":
      return <GradeSheetTab {...props} />;
    case "avance":
      return <CaptureProgressTab {...props} />;
    case "recuperacion":
      return <RecoveryTab {...props} />;
    case "resultados":
      return <ResultsTab {...props} />;
    default:
      return <UnitsTab {...props} />;
  }
}

/**
 * Evaluación (docs/ux-ui.md 1.5 y 2.11): una ruta con pestañas (`?tab=`) en vez
 * de ventanas apiladas. El ciclo elegido vive en la URL (`?ciclo=`) y, sin él,
 * se muestra el ciclo activo. Unidades, planilla, avance, recuperación y
 * resultados cuelgan del ciclo, como en el backend.
 */
export function EvaluationPage() {
  const { can } = usePermissions();
  const [params, setParams] = useSearchParams();

  const cycles = useQuery({
    queryKey: queryKeys.evaluation("", "cycles"),
    queryFn: () => cyclesService.list({ page_size: 100 }),
    select: (page) => page?.results ?? [],
  });
  const cycleList = cycles.data ?? [];
  const cycle =
    cycleList.find((item) => item.public_id === params.get("ciclo")) ??
    cycleList.find((item) => item.status === "active") ??
    cycleList[0] ??
    null;

  const tabs = TABS.filter(([, , codes]) => can(codes));
  const requested = params.get("tab");
  const current = tabs.some(([id]) => id === requested)
    ? requested
    : (tabs[0]?.[0] ?? "unidades");
  const [visited, setVisited] = useState([current]);
  useEffect(() => {
    setVisited((list) => (list.includes(current) ? list : [...list, current]));
  }, [current]);

  const goTo = (tab, extra = {}) =>
    setParams((existing) => {
      const next = new URLSearchParams(existing);
      next.set("tab", tab);
      for (const [key, value] of Object.entries(extra)) {
        if (value) next.set(key, value);
        else next.delete(key);
      }
      return next;
    });

  const changeCycle = (cycleId) => {
    setParams((existing) => {
      const next = new URLSearchParams(existing);
      next.set("ciclo", cycleId);
      for (const key of [...next.keys()]) {
        if (CYCLE_SCOPED.includes(key) || key.includes("_")) next.delete(key);
      }
      return next;
    });
    setVisited([current]);
  };

  return (
    <>
      <PageHeader
        breadcrumb="Gestión académica"
        subtitle="Configuración de unidades, planilla de calificaciones, avance de captura, recuperación y resultados del ciclo."
        title="Evaluación"
      />
      {cycles.error ? (
        <Alert severity="error">{cycles.error.message}</Alert>
      ) : null}
      <SectionCard sx={{ p: { xs: 2, sm: 3 } }}>
        <Stack gap={2}>
          <FilterBar>
            <FilterSelect
              label="Ciclo escolar"
              loading={cycles.isPending}
              minWidth={260}
              onChange={changeCycle}
              options={cycleList.map((item) => ({
                value: item.public_id,
                label: `${item.name} · ${CYCLE_STATUS_LABEL[item.status] ?? item.status}`,
              }))}
              value={cycle?.public_id ?? ""}
            />
          </FilterBar>
          {!cycle ? (
            cycles.isPending ? (
              <Typography role="status">Cargando ciclos…</Typography>
            ) : (
              <EmptyState message="No hay ciclos escolares registrados. Cree uno en Ciclo escolar para configurar su evaluación." />
            )
          ) : (
            <>
              <Tabs
                allowScrollButtonsMobile
                aria-label="Partes de la evaluación"
                onChange={(_event, next) => goTo(next)}
                scrollButtons="auto"
                value={current}
                variant="scrollable"
              >
                {tabs.map(([id, label]) => (
                  <Tab
                    aria-controls={`evaluation-panel-${id}`}
                    id={`evaluation-tab-${id}`}
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
                    aria-labelledby={`evaluation-tab-${id}`}
                    hidden={id !== current}
                    id={`evaluation-panel-${id}`}
                    key={`${id}-${cycle.public_id}`}
                    role="tabpanel"
                  >
                    <TabPanel
                      cycle={cycle}
                      cycles={cycleList}
                      goTo={goTo}
                      id={id}
                    />
                  </Box>
                ))}
              </Suspense>
            </>
          )}
        </Stack>
      </SectionCard>
    </>
  );
}
