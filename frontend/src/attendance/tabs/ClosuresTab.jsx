import { lazy, Suspense, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import TaskAltOutlinedIcon from "@mui/icons-material/TaskAltOutlined";

import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { attendanceService } from "@attendance/attendanceService.js";
import {
  useSectionCatalog,
  useShiftCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import {
  formatDate,
  formatPercent,
  todayInputValue,
} from "@shared/utils/format.js";
import { StatCard } from "@ui/display/StatCard.jsx";
import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";
import { DateField } from "@ui/forms/DateField.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";

const SectionClosureWindow = lazy(() =>
  import("../SectionClosureWindow.jsx").then((module) => ({
    default: module.SectionClosureWindow,
  }))
);

const BODY_SX = { px: { xs: 2, md: 3 }, py: 2.5 };

/** Cierre declarado por sección (RF-ASI-011/013): se abre en su ventana. */
function SectionClosureCard() {
  const [open, setOpen] = useState(false);
  return (
    <SectionCard
      action={
        <Button
          onClick={() => setOpen(true)}
          startIcon={<TaskAltOutlinedIcon fontSize="small" />}
          variant="contained"
        >
          Cerrar sección
        </Button>
      }
      sx={{ height: "100%" }}
      title="Cierre declarado por sección"
    >
      <Typography color="text.secondary" sx={BODY_SX} variant="body2">
        Declara la salida de quienes siguen presentes en una sección. Primero se
        previsualiza a quién alcanza; un docente de cobertura confirma una
        segunda vez y la acción queda auditada.
      </Typography>
      <Suspense
        fallback={
          <CircularProgress aria-label="Cargando cierre de sección" size={24} />
        }
      >
        {open ? (
          <SectionClosureWindow
            onClose={() => setOpen(false)}
            onClosed={() => {}}
            previewClosure={attendanceService.previewSectionClosure}
            submitClosure={attendanceService.closeSection}
          />
        ) : null}
      </Suspense>
    </SectionCard>
  );
}

/** Cierre de jornada (RF-JOR-004/005): recalcula el día y emite alertas. */
function JornadaClosureCard() {
  const shifts = useShiftCatalog();
  const [shiftId, setShiftId] = useState("");
  const [eventDate, setEventDate] = useState(todayInputValue);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const close = async () => {
    setConfirming(false);
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(
        await attendanceService.closeJornada({
          shift_id: shiftId,
          event_date: eventDate,
        })
      );
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const shiftLabel =
    shifts.options.find((option) => option.value === shiftId)?.label ?? "";

  return (
    <SectionCard sx={{ height: "100%" }} title="Cierre de jornada">
      <Stack gap={2} sx={BODY_SX}>
        <Typography color="text.secondary" variant="body2">
          Calcula el estado del día de cada estudiante de la jornada y emite las
          alertas de permanencia sin cierre e inconsistencias.
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} gap={2}>
          <FormSelect
            error={shifts.error}
            fullWidth
            label="Jornada"
            loading={shifts.loading}
            onChange={(event) => setShiftId(event.target.value)}
            options={shifts.options}
            placeholder="Seleccione una jornada"
            required
            value={shiftId}
          />
          <DateField
            label="Día"
            onChange={(event) => setEventDate(event.target.value)}
            required
            value={eventDate}
          />
        </Stack>
        <Box>
          <Button
            disabled={!shiftId || !eventDate || busy}
            onClick={() => setConfirming(true)}
            variant="contained"
          >
            {busy ? "Cerrando…" : "Cerrar jornada"}
          </Button>
        </Box>
        {error ? (
          <Alert role="alert" severity="error">
            {error}
          </Alert>
        ) : null}
        {result ? (
          <Alert severity="success">
            Jornada cerrada el {formatDate(result.event_date)}:{" "}
            {result.statuses?.length ?? 0} estudiantes con estado calculado y{" "}
            {result.alerts?.length ?? 0} alertas emitidas.
          </Alert>
        ) : null}
      </Stack>
      <ConfirmDialog
        busy={busy}
        confirmText="Cerrar jornada"
        message={`Se calcula el estado del día ${formatDate(eventDate)} en ${shiftLabel} y se emiten las alertas que correspondan. Queda auditado.`}
        onClose={() => setConfirming(false)}
        onConfirm={close}
        open={confirming}
        title="Cerrar jornada"
      />
    </SectionCard>
  );
}

/**
 * Razón de cobertura (AS5; RF-ASI-013): qué parte de los cierres declarados
 * hizo un docente de cobertura. Sección y fechas son filtros opcionales.
 */
function CoverageRatioCard() {
  const sections = useSectionCatalog();
  const [sectionId, setSectionId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const consult = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    try {
      setResult(
        await attendanceService.coverageRatio({
          section_id: sectionId,
          date_from: dateFrom,
          date_to: dateTo,
        })
      );
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <SectionCard
      subtitle="Cierres declarados por un docente de cobertura"
      title="Razón de cobertura de cierres"
    >
      <Stack component="form" gap={2} onSubmit={consult} sx={BODY_SX}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "2fr 1fr 1fr" },
            gap: 2,
          }}
        >
          <FormSelect
            error={sections.error}
            fullWidth
            helperText="Opcional; sin sección cuenta todas."
            label="Sección"
            loading={sections.loading}
            onChange={(event) => setSectionId(event.target.value)}
            options={sections.options}
            placeholder="Todas las secciones"
            value={sectionId}
          />
          <DateField
            label="Desde"
            onChange={(event) => setDateFrom(event.target.value)}
            value={dateFrom}
          />
          <DateField
            label="Hasta"
            onChange={(event) => setDateTo(event.target.value)}
            value={dateTo}
          />
        </Box>
        <Box>
          <Button disabled={busy} type="submit" variant="contained">
            {busy ? "Consultando…" : "Consultar"}
          </Button>
        </Box>
        {error ? (
          <Alert role="alert" severity="error">
            {error}
          </Alert>
        ) : null}
        {result ? (
          <StatCard
            hint={`${result.covering_closures} de ${result.total_closures} cierres declarados por cobertura`}
            label="Razón de cobertura"
            value={
              result.coverage_ratio == null
                ? "Sin cierres"
                : formatPercent(result.coverage_ratio * 100)
            }
          />
        ) : null}
      </Stack>
    </SectionCard>
  );
}

/**
 * Cierres (AS5, AS6): cierre declarado por sección (`attendance.declared_close`),
 * cierre de jornada y razón de cobertura (`attendance.jornada.configure`).
 */
export function ClosuresTab() {
  const { can } = usePermissions();
  const canDeclare = can(PERMISSION.ATTENDANCE_DECLARED_CLOSE);
  const canConfigure = can(PERMISSION.ATTENDANCE_JORNADA_CONFIGURE);

  return (
    <Stack gap={2}>
      <Grid container spacing={2}>
        {canDeclare ? (
          <Grid size={{ xs: 12, lg: 6 }}>
            <SectionClosureCard />
          </Grid>
        ) : null}
        {canConfigure ? (
          <Grid size={{ xs: 12, lg: 6 }}>
            <JornadaClosureCard />
          </Grid>
        ) : null}
      </Grid>
      {canConfigure ? <CoverageRatioCard /> : null}
    </Stack>
  );
}
