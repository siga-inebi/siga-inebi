import { Link as RouterLink } from "react-router-dom";

import ArrowForwardRoundedIcon from "@mui/icons-material/ArrowForwardRounded";
import CalendarMonthOutlinedIcon from "@mui/icons-material/CalendarMonthOutlined";
import CheckCircleOutlineRoundedIcon from "@mui/icons-material/CheckCircleOutlineRounded";
import NotificationsActiveOutlinedIcon from "@mui/icons-material/NotificationsActiveOutlined";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import ButtonBase from "@mui/material/ButtonBase";
import Grid from "@mui/material/Grid";
import LinearProgress from "@mui/material/LinearProgress";
import Skeleton from "@mui/material/Skeleton";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { NAV_GROUPS, canViewModule, prefetchModule } from "@app/navigation.js";
import { useAuth } from "@auth/useAuth.js";
import { formatDateLong, formatFullName } from "@shared/utils/format.js";
import { palette } from "@theme/tokens/color.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";

import { useDashboardSummary } from "./useDashboardSummary.js";

const LONG_DATE = new Intl.DateTimeFormat("es-GT", {
  weekday: "long",
  day: "numeric",
  month: "long",
  timeZone: "America/Guatemala",
});

const ALERT_LABEL = {
  ausente_sin_registro: "Ausencia sin registro",
  permanencia_sin_cierre: "Permanencia sin cierre",
  frecuencia_ausencias: "Ausencias frecuentes",
  inconsistencia: "Inconsistencia",
};

const SHORTCUT_ORDER = [
  "asistencia",
  "matriculas",
  "alumnos",
  "evaluacion",
  "alertas",
  "ciclos",
];

function cycleProgress(cycle, now = new Date()) {
  if (!cycle?.starts_on || !cycle?.ends_on) return 0;
  const start = new Date(`${cycle.starts_on}T12:00:00`);
  const end = new Date(`${cycle.ends_on}T12:00:00`);
  const total = end.getTime() - start.getTime();
  if (total <= 0) return 0;
  return Math.min(100, Math.max(0, ((now.getTime() - start) / total) * 100));
}

function dashboardHeroSx(theme) {
  const colors = palette(theme).surfaces;
  return {
    position: "relative",
    overflow: "hidden",
    px: { xs: 3, md: 4.5 },
    py: { xs: 3.5, md: 4.5 },
    color: colors.dashboardHeroText,
    backgroundImage: `linear-gradient(125deg, ${colors.dashboardHeroStart}, ${colors.dashboardHeroEnd})`,
    borderRadius: theme.tokens.radii.card,
    "&::after": {
      content: '""',
      position: "absolute",
      inset: "auto -4% -42% auto",
      width: 250,
      aspectRatio: "1",
      border: "1px solid",
      borderColor: colors.dashboardHeroAccent,
      borderRadius: "50%",
      opacity: 0.55,
    },
  };
}

function dashboardHeroActionSx(theme) {
  const colors = palette(theme).surfaces;
  return {
    bgcolor: colors.dashboardHeroAction,
    color: colors.dashboardHeroActionText,
    "&:hover": { bgcolor: colors.dashboardHeroActionHover },
  };
}

function Metric({ label, loading, tone = "primary", value }) {
  return (
    <Box
      sx={{
        minHeight: 118,
        p: 2.5,
        bgcolor: "background.paper",
        border: "1px solid",
        borderColor: "divider",
        borderTop: "3px solid",
        borderTopColor: `${tone}.main`,
      }}
    >
      <Typography color="text.secondary" variant="overline">
        {label}
      </Typography>
      {loading ? (
        <Skeleton height={45} width={82} />
      ) : (
        <Typography
          sx={{
            fontSize: "2.25rem",
            fontWeight: 750,
            lineHeight: 1.15,
            mt: 0.5,
          }}
        >
          {value ?? "—"}
        </Typography>
      )}
    </Box>
  );
}

function ActionTile({ item }) {
  const Icon = item.icon;
  return (
    <ButtonBase
      component={RouterLink}
      onFocus={() => prefetchModule(item)}
      onPointerEnter={() => prefetchModule(item)}
      sx={(theme) => ({
        alignItems: "stretch",
        justifyContent: "stretch",
        width: "100%",
        height: "100%",
        minHeight: 126,
        textAlign: "left",
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
        borderRadius: theme.tokens.radii.card,
        transition: "transform 160ms ease, border-color 160ms ease",
        "&:hover": {
          transform: "translateY(-2px)",
          borderColor: "primary.main",
        },
        "@media (prefers-reduced-motion: reduce)": { transition: "none" },
      })}
      to={item.path}
    >
      <Stack sx={{ width: "100%", p: 2.25 }}>
        <Stack
          alignItems="center"
          direction="row"
          justifyContent="space-between"
        >
          <Box
            sx={{
              display: "grid",
              placeItems: "center",
              width: 38,
              height: 38,
              bgcolor: "action.hover",
              color: "primary.main",
              borderRadius: 1,
            }}
          >
            <Icon fontSize="small" />
          </Box>
          <ArrowForwardRoundedIcon color="action" fontSize="small" />
        </Stack>
        <Typography sx={{ mt: 2, fontWeight: 700 }}>{item.label}</Typography>
        <Typography color="text.secondary" sx={{ mt: 0.5 }} variant="body2">
          {item.description}
        </Typography>
      </Stack>
    </ButtonBase>
  );
}

function PriorityItem({ children, label, to, variant = "warning" }) {
  return (
    <Stack
      alignItems={{ xs: "flex-start", sm: "center" }}
      direction={{ xs: "column", sm: "row" }}
      gap={1.5}
      sx={{ py: 1.5, borderBottom: "1px solid", borderColor: "divider" }}
    >
      <StatusChip label={label} variant={variant} />
      <Typography sx={{ flex: 1 }} variant="body2">
        {children}
      </Typography>
      <Button
        component={RouterLink}
        endIcon={<ArrowForwardRoundedIcon />}
        size="small"
        to={to}
        variant="text"
      >
        Resolver
      </Button>
    </Stack>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const summary = useDashboardSummary(user);
  const displayName =
    formatFullName(user?.person) !== "—"
      ? formatFullName(user.person).split(" ")[0]
      : user?.username;

  const allItems = NAV_GROUPS.flatMap((group) => group.items);
  const shortcuts = SHORTCUT_ORDER.map((key) =>
    allItems.find((item) => item.key === key)
  )
    .filter(Boolean)
    .filter((item) => canViewModule(user, item));

  const primaryAction = summary.pendingAlerts
    ? { label: "Atender alertas", to: "/app/alertas" }
    : summary.activeCycle
      ? {
          label: "Abrir ciclo activo",
          to: `/app/ciclos/${summary.activeCycle.public_id}`,
        }
      : { label: "Preparar ciclo escolar", to: "/app/ciclos" };

  const progress = cycleProgress(summary.activeCycle);
  const hasPriorities =
    !summary.activeCycle ||
    Boolean(summary.pendingAlerts) ||
    Boolean(summary.draftCycle);

  return (
    <Stack gap={3}>
      <Box component="header" sx={dashboardHeroSx}>
        <Grid container spacing={3} sx={{ position: "relative", zIndex: 1 }}>
          <Grid size={{ xs: 12, md: 8 }}>
            <Typography sx={{ opacity: 0.8 }} variant="overline">
              {LONG_DATE.format(new Date())}
            </Typography>
            <Typography component="h1" sx={{ mt: 0.75 }} variant="h4">
              Buen día, {displayName}
            </Typography>
            <Typography sx={{ mt: 1.25, maxWidth: 620, opacity: 0.82 }}>
              Aquí está lo importante para mover la jornada, atender pendientes
              y mantener el ciclo escolar bajo control.
            </Typography>
          </Grid>
          <Grid
            alignItems={{ xs: "flex-start", md: "flex-end" }}
            display="flex"
            justifyContent={{ xs: "flex-start", md: "flex-end" }}
            size={{ xs: 12, md: 4 }}
          >
            <Button
              component={RouterLink}
              endIcon={<ArrowForwardRoundedIcon />}
              sx={dashboardHeroActionSx}
              to={primaryAction.to}
              variant="contained"
            >
              {primaryAction.label}
            </Button>
          </Grid>
        </Grid>
      </Box>

      <Grid container spacing={1.5}>
        <Grid size={{ xs: 6, lg: 3 }}>
          <Metric
            label="Estudiantes"
            loading={summary.loading}
            value={summary.counts.students}
          />
        </Grid>
        <Grid size={{ xs: 6, lg: 3 }}>
          <Metric
            label="Matrículas activas"
            loading={summary.loading}
            tone="success"
            value={summary.activeEnrolments}
          />
        </Grid>
        <Grid size={{ xs: 6, lg: 3 }}>
          <Metric
            label="Docentes"
            loading={summary.loading}
            value={summary.counts.teachers}
          />
        </Grid>
        <Grid size={{ xs: 6, lg: 3 }}>
          <Metric
            label="Alertas por atender"
            loading={summary.loading}
            tone={summary.pendingAlerts ? "error" : "success"}
            value={summary.pendingAlerts}
          />
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 7 }}>
          <SectionCard
            subtitle="Panorama académico actual"
            sx={{ height: "100%" }}
            title="Ciclo escolar"
          >
            <Box sx={{ p: { xs: 2.5, md: 3 } }}>
              {summary.activeCycle ? (
                <Stack gap={2.25}>
                  <Stack
                    alignItems={{ xs: "flex-start", sm: "center" }}
                    direction={{ xs: "column", sm: "row" }}
                    justifyContent="space-between"
                  >
                    <Box>
                      <Typography variant="h5">
                        {summary.activeCycle.name}
                      </Typography>
                      <Typography
                        color="text.secondary"
                        sx={{ mt: 0.5 }}
                        variant="body2"
                      >
                        {formatDateLong(summary.activeCycle.starts_on)} —{" "}
                        {formatDateLong(summary.activeCycle.ends_on)}
                      </Typography>
                    </Box>
                    <StatusChip label="Ciclo activo" variant="success" />
                  </Stack>
                  <Box>
                    <Stack
                      direction="row"
                      justifyContent="space-between"
                      sx={{ mb: 0.75 }}
                    >
                      <Typography color="text.secondary" variant="body2">
                        Avance del calendario
                      </Typography>
                      <Typography fontWeight={700} variant="body2">
                        {Math.round(progress)} %
                      </Typography>
                    </Stack>
                    <LinearProgress
                      aria-label="Avance del ciclo escolar"
                      value={progress}
                      variant="determinate"
                    />
                  </Box>
                  <Button
                    component={RouterLink}
                    endIcon={<ArrowForwardRoundedIcon />}
                    sx={{ alignSelf: "flex-start" }}
                    to={`/app/ciclos/${summary.activeCycle.public_id}`}
                    variant="outlined"
                  >
                    Ver estructura y preparación
                  </Button>
                </Stack>
              ) : (
                <Stack alignItems="flex-start" gap={1.5}>
                  <CalendarMonthOutlinedIcon color="warning" />
                  <Typography variant="h6">No hay un ciclo activo</Typography>
                  <Typography color="text.secondary" variant="body2">
                    Prepare y valide la estructura académica antes de iniciar la
                    operación del establecimiento.
                  </Typography>
                  <Button
                    component={RouterLink}
                    to="/app/ciclos"
                    variant="contained"
                  >
                    Ir a ciclos
                  </Button>
                </Stack>
              )}
            </Box>
          </SectionCard>
        </Grid>

        <Grid size={{ xs: 12, lg: 5 }}>
          <SectionCard
            subtitle="Lo que conviene resolver primero"
            sx={{ height: "100%" }}
            title="Atención prioritaria"
          >
            <Box sx={{ px: 3, pb: 1.5 }}>
              {!summary.activeCycle ? (
                <PriorityItem
                  label="Bloqueante"
                  to="/app/ciclos"
                  variant="danger"
                >
                  Active un ciclo escolar para habilitar la operación académica.
                </PriorityItem>
              ) : null}
              {summary.pendingAlerts ? (
                <PriorityItem
                  label={`${summary.pendingAlerts} alertas`}
                  to="/app/alertas"
                  variant="danger"
                >
                  Hay alertas activas que todavía no han sido atendidas.
                </PriorityItem>
              ) : null}
              {summary.draftCycle ? (
                <PriorityItem
                  label="En preparación"
                  to={`/app/ciclos/${summary.draftCycle.public_id}`}
                >
                  Continúe preparando {summary.draftCycle.name} antes de su
                  activación.
                </PriorityItem>
              ) : null}
              {!hasPriorities ? (
                <Stack
                  alignItems="center"
                  gap={1.25}
                  sx={{ py: 4, textAlign: "center" }}
                >
                  <CheckCircleOutlineRoundedIcon color="success" />
                  <Typography fontWeight={700}>
                    Sin pendientes detectados
                  </Typography>
                  <Typography color="text.secondary" variant="body2">
                    El ciclo está activo y no hay alertas institucionales
                    abiertas.
                  </Typography>
                </Stack>
              ) : null}
            </Box>
          </SectionCard>
        </Grid>
      </Grid>

      {summary.recentAlerts.length ? (
        <SectionCard
          subtitle="Últimos casos sin atender"
          title="Alertas recientes"
        >
          <Grid container spacing={0} sx={{ px: 3, pb: 2 }}>
            {summary.recentAlerts.map((alert) => (
              <Grid key={alert.public_id} size={{ xs: 12, md: 4 }}>
                <Stack gap={0.5} sx={{ py: 1.5, pr: 2 }}>
                  <Stack alignItems="center" direction="row" gap={1}>
                    <NotificationsActiveOutlinedIcon
                      color="error"
                      fontSize="small"
                    />
                    <Typography fontWeight={700} variant="body2">
                      {ALERT_LABEL[alert.alert_type] ?? "Alerta institucional"}
                    </Typography>
                  </Stack>
                  <Typography color="text.secondary" variant="body2">
                    Jornada del {formatDateLong(alert.event_date)}
                  </Typography>
                </Stack>
              </Grid>
            ))}
          </Grid>
        </SectionCard>
      ) : null}

      <Box component="section">
        <Typography color="text.secondary" component="h2" variant="overline">
          Acciones frecuentes
        </Typography>
        <Grid container spacing={1.5} sx={{ mt: 0.5 }}>
          {shortcuts.map((item) => (
            <Grid key={item.key} size={{ xs: 12, sm: 6, lg: 4 }}>
              <ActionTile item={item} />
            </Grid>
          ))}
        </Grid>
      </Box>
    </Stack>
  );
}
