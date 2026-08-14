import { Link as RouterLink } from "react-router-dom";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { NAV_GROUPS, prefetchModule } from "@app/navigation.js";
import { useAuth } from "@auth/useAuth.js";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { QuickActionCard } from "@ui/display/QuickActionCard.jsx";
import { StatCard } from "@ui/display/StatCard.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";
import { formatFullName } from "@shared/utils/format.js";

import { useDashboardSummary } from "./useDashboardSummary.js";

/** Etiqueta de grupo del panel. Misma tipografia que los grupos del menu. */
function GroupLabel({ children }) {
  return (
    <Typography
      component="p"
      sx={{ color: "text.secondary", mb: 1 }}
      variant="overline"
    >
      {children}
    </Typography>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const { counts, health, loading } = useDashboardSummary();

  const displayName =
    formatFullName(user?.person) !== "—"
      ? formatFullName(user.person)
      : user?.username;

  // Los accesos rapidos salen del mismo registro que el menu lateral: si se
  // agrega un modulo, aparece en los dos lados sin tocar esta pantalla.
  const shortcuts = NAV_GROUPS.flatMap((group) => group.items)
    .filter((item) => !item.canView || item.canView(user))
    .slice(0, 4);

  return (
    <>
      <PageHeader
        subtitle={`Buen dia, ${displayName}. Resumen del establecimiento y accesos rapidos.`}
        title="Panel"
      />

      <Box sx={{ mb: 3 }}>
        <GroupLabel>Accesos rapidos</GroupLabel>
        <Grid container spacing={2}>
          {shortcuts.map((item) => (
            <Grid key={item.key} size={{ xs: 12, sm: 6, lg: 3 }}>
              <QuickActionCard
                description={item.description}
                onPointerEnter={() => prefetchModule(item)}
                title={item.label}
                to={item.path}
              />
            </Grid>
          ))}
        </Grid>
      </Box>

      <Box sx={{ mb: 3 }}>
        <GroupLabel>Resumen del establecimiento</GroupLabel>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 4 }}>
            <StatCard
              action={
                <Button component={RouterLink} size="small" to="/app/alumnos" variant="text">
                  Ver listado
                </Button>
              }
              label="Estudiantes"
              loading={loading}
              value={counts.students ?? "—"}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <StatCard label="Docentes" loading={loading} value={counts.teachers ?? "—"} />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <StatCard
              label="Padres de familia"
              loading={loading}
              value={counts.guardians ?? "—"}
            />
          </Grid>
        </Grid>
      </Box>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <SectionCard subtitle="Cuenta institucional en uso" title="Identidad actual">
            <Stack component="dl" gap={2} sx={{ px: 3, py: 2.5, m: 0 }}>
              <IdentityRow label="Usuario" value={user?.username} />
              <IdentityRow label="Correo" value={user?.email || "No definido"} />
              <IdentityRow
                label="Estado"
                value={
                  <StatusChip
                    label={user?.status ?? "desconocido"}
                    variant={user?.status === "active" ? "success" : "neutral"}
                  />
                }
              />
            </Stack>
          </SectionCard>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <SectionCard subtitle="Conexion con la API" title="Estado del servicio">
            <Stack gap={1.5} sx={{ px: 3, py: 2.5 }}>
              {health.error ? (
                <Stack alignItems="center" direction="row" gap={1}>
                  <StatusChip label="Sin conexion" variant="danger" />
                  <Typography color="text.secondary" variant="body2">
                    {health.error}
                  </Typography>
                </Stack>
              ) : (
                <Stack alignItems="center" direction="row" gap={1}>
                  <StatusChip
                    label={health.data ? "Operativo" : "Verificando…"}
                    variant={health.data ? "success" : "neutral"}
                  />
                  {health.data ? (
                    <Typography color="text.secondary" variant="body2">
                      {health.data.service}: {health.data.status}
                    </Typography>
                  ) : null}
                </Stack>
              )}
            </Stack>
          </SectionCard>
        </Grid>
      </Grid>
    </>
  );
}

function IdentityRow({ label, value }) {
  return (
    <Box>
      <Typography
        component="dt"
        sx={{ fontSize: "0.75rem", color: "text.secondary", textTransform: "uppercase" }}
      >
        {label}
      </Typography>
      <Box component="dd" sx={{ m: 0, mt: 0.5, fontSize: "0.875rem" }}>
        {value}
      </Box>
    </Box>
  );
}
