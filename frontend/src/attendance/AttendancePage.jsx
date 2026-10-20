import { lazy, Suspense, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";

import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import {
  CAMERA_ERROR_MESSAGES,
  CameraAccessError,
  createCameraSession,
} from "@shared/platform/camera.js";
import { EmptyState } from "@ui/feedback/EmptyState.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";

const named = (load, name) =>
  lazy(() => load().then((m) => ({ default: m[name] })));

// Cada pestaña es un chunk aparte: la ruta solo descarga la que se abre.
const TodayTab = named(() => import("./tabs/TodayTab.jsx"), "TodayTab");
const MovementsTab = named(
  () => import("./tabs/MovementsTab.jsx"),
  "MovementsTab"
);
const ClosuresTab = named(
  () => import("./tabs/ClosuresTab.jsx"),
  "ClosuresTab"
);
const RequestsTab = named(
  () => import("./tabs/RequestsTab.jsx"),
  "RequestsTab"
);
const CardsTab = named(() => import("./tabs/CardsTab.jsx"), "CardsTab");
const SettingsTab = named(
  () => import("./tabs/SettingsTab.jsx"),
  "SettingsTab"
);

const P = PERMISSION;

/** Pestañas y los permisos que bastan para verlas (basta uno). */
const TABS = [
  ["hoy", "Hoy", [P.ATTENDANCE_SCAN, P.STUDENT_VIEW_BASIC]],
  [
    "movimientos",
    "Movimientos",
    [
      P.STUDENT_VIEW_BASIC,
      P.ATTENDANCE_RECORD_MANUAL,
      P.ATTENDANCE_SCAN,
      P.ATTENDANCE_DECLARED_CLOSE,
    ],
  ],
  [
    "cierres",
    "Cierres",
    [P.ATTENDANCE_DECLARED_CLOSE, P.ATTENDANCE_JORNADA_CONFIGURE],
  ],
  [
    "solicitudes",
    "Justificaciones y permisos",
    [
      P.ATTENDANCE_JUSTIFICATION_REQUEST,
      P.ATTENDANCE_JUSTIFICATION_RESOLVE,
      P.ATTENDANCE_PERMIT_REQUEST,
      P.ATTENDANCE_PERMIT_RESOLVE,
    ],
  ],
  ["carnes", "Carnés", [P.ATTENDANCE_CREDENTIAL_ISSUE]],
  [
    "configuracion",
    "Configuración",
    [P.ATTENDANCE_JORNADA_CONFIGURE, P.ATTENDANCE_SCAN],
  ],
];

function TabPanel({ id }) {
  switch (id) {
    case "movimientos":
      return <MovementsTab />;
    case "cierres":
      return <ClosuresTab />;
    case "solicitudes":
      return <RequestsTab />;
    case "carnes":
      return <CardsTab />;
    case "configuracion":
      return <SettingsTab />;
    default:
      return <TodayTab />;
  }
}

/**
 * Asistencia (docs/ux-ui.md 2.12, AS6): una ruta con pestañas (`?tab=`) en vez
 * de seis botones que abrían ventanas sueltas. Cada pestaña se descarga al
 * abrirla y solo aparece con su permiso; el backend vuelve a autorizar cada
 * operación.
 *
 * RNF-PRI-003: nada de lo que se consulta aquí se guarda en el dispositivo; el
 * estado vive en memoria y en la URL solo van filtros e identificadores.
 */
export function AttendancePage() {
  const { can } = usePermissions();
  const [params, setParams] = useSearchParams();
  const canScan = can(P.ATTENDANCE_SCAN);

  const tabs = TABS.filter(([, , codes]) => can(codes));
  const requested = params.get("tab");
  const current = tabs.some(([id]) => id === requested)
    ? requested
    : (tabs[0]?.[0] ?? "hoy");
  const [visited, setVisited] = useState([current]);
  useEffect(() => {
    setVisited((list) => (list.includes(current) ? list : [...list, current]));
  }, [current]);

  const [cameraPreflightError, setCameraPreflightError] = useState(null);

  // RNF-USA-001: el permiso de cámara se verifica al entrar a la captura de
  // asistencia, no en el primer escaneo. La sesión se libera de inmediato: solo
  // importa que el navegador haya resuelto el permiso. Solo para quien escanea:
  // a quien revisa justificaciones no se le pide la cámara.
  useEffect(() => {
    if (!canScan) return undefined;
    let disposed = false;
    createCameraSession()
      .then((session) => {
        session.stop();
        if (!disposed) setCameraPreflightError(null);
      })
      .catch((error) => {
        if (disposed) return;
        setCameraPreflightError(
          error instanceof CameraAccessError ? error.code : "unavailable"
        );
      });
    return () => {
      disposed = true;
    };
  }, [canScan]);

  const goTo = (tab) =>
    setParams((existing) => {
      const next = new URLSearchParams(existing);
      next.set("tab", tab);
      return next;
    });

  return (
    <>
      <PageHeader
        breadcrumb="Control de asistencia"
        subtitle="Captura del día, movimientos, cierres, justificaciones y permisos, carnés y configuración de la jornada."
        title="Asistencia"
      />

      {cameraPreflightError ? (
        <Alert
          onClose={() => setCameraPreflightError(null)}
          severity="warning"
          sx={{ mb: 2 }}
        >
          {CAMERA_ERROR_MESSAGES[cameraPreflightError] ??
            CAMERA_ERROR_MESSAGES.unavailable}
        </Alert>
      ) : null}

      <SectionCard sx={{ p: { xs: 2, sm: 3 } }}>
        {tabs.length === 0 ? (
          <EmptyState message="Su cuenta no tiene permisos de asistencia. Pídalos a administración." />
        ) : (
          <Stack gap={2}>
            <Tabs
              allowScrollButtonsMobile
              aria-label="Partes de la asistencia"
              onChange={(_event, next) => goTo(next)}
              scrollButtons="auto"
              value={current}
              variant="scrollable"
            >
              {tabs.map(([id, label]) => (
                <Tab
                  aria-controls={`attendance-panel-${id}`}
                  id={`attendance-tab-${id}`}
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
                  aria-labelledby={`attendance-tab-${id}`}
                  hidden={id !== current}
                  id={`attendance-panel-${id}`}
                  key={id}
                  role="tabpanel"
                >
                  <TabPanel id={id} />
                </Box>
              ))}
            </Suspense>
          </Stack>
        )}
      </SectionCard>
    </>
  );
}
