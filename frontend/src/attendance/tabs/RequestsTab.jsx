import { lazy, Suspense } from "react";
import { useSearchParams } from "react-router-dom";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";

// Cada bandeja es un chunk aparte: se descarga la que se abre.
const JustificationsQueue = lazy(() =>
  import("../requests/justifications.jsx").then((module) => ({
    default: module.JustificationsQueue,
  }))
);
const PermitsQueue = lazy(() =>
  import("../requests/permits.jsx").then((module) => ({
    default: module.PermitsQueue,
  }))
);

const P = PERMISSION;

const QUEUES = [
  [
    "justificaciones",
    "Justificaciones",
    JustificationsQueue,
    [P.ATTENDANCE_JUSTIFICATION_REQUEST, P.ATTENDANCE_JUSTIFICATION_RESOLVE],
  ],
  [
    "permisos",
    "Permisos de salida",
    PermitsQueue,
    [P.ATTENDANCE_PERMIT_REQUEST, P.ATTENDANCE_PERMIT_RESOLVE],
  ],
];

/**
 * Justificaciones y permisos (AS3, AS4): dos bandejas con la misma forma. La
 * elegida vive en la URL (`?bandeja=`) para volver a ella con atrás o un
 * enlace.
 */
export function RequestsTab() {
  const { can } = usePermissions();
  const [params, setParams] = useSearchParams();
  const queues = QUEUES.filter(([, , , codes]) => can(codes));
  const requested = params.get("bandeja");
  const current =
    queues.find(([id]) => id === requested) ?? queues[0] ?? QUEUES[0];
  const Queue = current[2];

  return (
    <Stack gap={2}>
      {queues.length > 1 ? (
        <Stack aria-label="Bandeja" direction="row" gap={1} role="group">
          {queues.map(([id, label]) => (
            <Button
              aria-pressed={id === current[0]}
              key={id}
              onClick={() =>
                setParams((existing) => {
                  const next = new URLSearchParams(existing);
                  next.set("bandeja", id);
                  return next;
                })
              }
              size="small"
              variant={id === current[0] ? "contained" : "outlined"}
            >
              {label}
            </Button>
          ))}
        </Stack>
      ) : null}
      <Suspense
        fallback={<Typography role="status">Cargando bandeja…</Typography>}
      >
        <Queue key={current[0]} />
      </Suspense>
    </Stack>
  );
}
