import { lazy, Suspense, useState } from "react";

import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import GroupsOutlinedIcon from "@mui/icons-material/GroupsOutlined";

import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";

import { AttendancePercentageProbe } from "../AttendancePercentageProbe.jsx";
import { CaptureShiftCard } from "../CaptureShiftCard.jsx";
import { DayStatusProbe } from "../DayStatusProbe.jsx";

const AttendancePresenceWindow = lazy(() =>
  import("../AttendancePresenceWindow.jsx").then((module) => ({
    default: module.AttendancePresenceWindow,
  }))
);

/**
 * Hoy (AS1, AS6): el turno de captura con el escaneo, la presencia en tiempo
 * real y las consultas puntuales del estado del día y del porcentaje.
 * El turno exige `attendance.scan`; las consultas, `student.view_basic`.
 */
export function TodayTab() {
  const { can } = usePermissions();
  const canScan = can(PERMISSION.ATTENDANCE_SCAN);
  const canView = can(PERMISSION.STUDENT_VIEW_BASIC);
  const [showPresence, setShowPresence] = useState(false);

  return (
    <Stack gap={2}>
      {canScan ? <CaptureShiftCard /> : null}
      {canView ? (
        <>
          <Stack direction="row" justifyContent="flex-end">
            <Button
              onClick={() => setShowPresence(true)}
              startIcon={<GroupsOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              Presencia en tiempo real
            </Button>
          </Stack>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, lg: 6 }}>
              <DayStatusProbe />
            </Grid>
            <Grid size={{ xs: 12, lg: 6 }}>
              <AttendancePercentageProbe />
            </Grid>
          </Grid>
        </>
      ) : null}
      <Suspense fallback={null}>
        {showPresence ? (
          <AttendancePresenceWindow onClose={() => setShowPresence(false)} />
        ) : null}
      </Suspense>
    </Stack>
  );
}
