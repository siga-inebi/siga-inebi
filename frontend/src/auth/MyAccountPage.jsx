import { useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import {
  ACCOUNT_STATUS_VARIANT,
  ASSIGNMENT_STATUS_VARIANT,
  accountStatusLabel,
} from "@auth/accountLabels.js";
import { authService } from "@auth/authService.js";
import { useAuth } from "@auth/useAuth.js";
import { useInvalidate } from "@shared/api/invalidation.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";
import { formatDateTime } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";
import { DetailField } from "@ui/layout/DetailWindow.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

import { ChangePasswordWindow } from "./ChangePasswordWindow.jsx";
import { scopeDimensionsText } from "./scopeChoice.js";
import { SessionsTable } from "./SessionsTable.jsx";

function Grid({ children }) {
  return (
    <Box
      component="dl"
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: "repeat(3, 1fr)" },
        gap: 2.5,
        m: 0,
        px: 3,
        py: 2.5,
      }}
    >
      {children}
    </Box>
  );
}

/** Horario semanal propio (RF-HOR-010), solo para docentes y encargados. */
function MySchedule() {
  const { data, error, loading } = useResourceQuery(
    [...queryKeys.identity.me(), "schedule"],
    () => authService.mySchedule()
  );
  if (error) {
    return (
      <Typography color="text.secondary" sx={{ px: 3, py: 2 }} variant="body2">
        Su cuenta no tiene horario propio: el horario semanal es para docentes y
        encargados.
      </Typography>
    );
  }
  return (
    <SectionTableArea>
      <DataTable
        columns={[
          {
            key: "day",
            label: "Día",
            render: (row) => row.day_of_week_display,
          },
          {
            key: "block",
            label: "Bloque",
            render: (row) =>
              row.schedule_block?.name ??
              (row.schedule_block
                ? `Bloque ${row.schedule_block.number}`
                : "—"),
          },
          {
            key: "subject",
            label: "Curso",
            render: (row) => row.subject?.name ?? "—",
          },
          {
            key: "section",
            label: "Sección",
            render: (row) => row.section?.name ?? "—",
          },
        ]}
        emptyMessage="Sin clases en un horario publicado."
        getRowKey={(row) => row.public_id}
        loading={loading}
        rows={data?.results ?? []}
      />
    </SectionTableArea>
  );
}

/**
 * Mi cuenta (docs/ux-ui.md MC1): datos de la persona, mis roles y alcances
 * ("Docente · Sección 1.º Básico A · Matemática"), mi horario semanal y mis
 * sesiones. Cualquier cuenta autenticada la ve.
 */
export function MyAccountPage() {
  const { logout, logoutAll } = useAuth();
  const invalidate = useInvalidate();
  const [changingPassword, setChangingPassword] = useState(false);
  const [closingAll, setClosingAll] = useState(false);
  const [closeError, setCloseError] = useState("");
  const { data, error, loading } = useResourceQuery(
    queryKeys.identity.me(),
    () => authService.myAccount()
  );

  if (error) {
    return (
      <>
        <PageHeader title="Mi cuenta" />
        <Alert role="alert" severity="error">
          {error}
        </Alert>
      </>
    );
  }
  if (loading || !data) {
    return <PageHeader title="Mi cuenta" subtitle="Cargando…" />;
  }

  const { account, person, roles, sessions } = data;

  return (
    <>
      <PageHeader
        action={
          <Stack direction="row" gap={1}>
            <Button
              onClick={() => setChangingPassword(true)}
              variant="outlined"
            >
              Cambiar contraseña
            </Button>
          </Stack>
        }
        subtitle="Sus datos, sus roles con su alcance y sus sesiones abiertas."
        title="Mi cuenta"
      />

      <SectionCard title="Datos">
        <Grid>
          <DetailField
            label="Nombre"
            value={`${person.first_name} ${person.last_name}`}
          />
          <DetailField label="Usuario" value={account.username} />
          <DetailField label="Correo" value={account.email || person.email} />
          <DetailField label="Teléfono" value={person.phone_number} />
          <DetailField
            label="Estado"
            value={
              <StatusChip
                label={accountStatusLabel(account)}
                variant={ACCOUNT_STATUS_VARIANT[account.status] ?? "neutral"}
              />
            }
          />
          <DetailField
            label="Cierre por inactividad"
            value={`${data.session_idle_timeout_minutes} minutos (el mayor de sus roles)`}
          />
        </Grid>
      </SectionCard>

      <SectionCard
        subtitle="Lo que puede hacer y dónde. Si falta algo, pídalo a administración."
        title="Mis roles y alcances"
      >
        <SectionTableArea>
          <DataTable
            columns={[
              { key: "role_name", label: "Rol" },
              {
                key: "scopes",
                label: "Alcance",
                render: (row) =>
                  row.scopes.length ? (
                    row.scopes.map((scope) => (
                      <div key={scope.public_id}>
                        {scopeDimensionsText(scope)}
                      </div>
                    ))
                  ) : (
                    <MutedCell>Sin alcance</MutedCell>
                  ),
              },
              {
                key: "ends_at",
                label: "Vigente hasta",
                render: (row) =>
                  row.ends_at ? (
                    formatDateTime(row.ends_at)
                  ) : (
                    <MutedCell>Sin vencimiento</MutedCell>
                  ),
              },
              {
                key: "status",
                label: "Estado",
                render: (row) => (
                  <StatusChip
                    label={row.status_display}
                    variant={ASSIGNMENT_STATUS_VARIANT[row.status] ?? "neutral"}
                  />
                ),
              },
            ]}
            emptyMessage="Su cuenta no tiene roles vigentes."
            getRowKey={(row) => row.public_id}
            rows={roles}
          />
        </SectionTableArea>
      </SectionCard>

      <SectionCard title="Mi horario semanal">
        <MySchedule />
      </SectionCard>

      <SectionCard
        action={
          <Button
            color="error"
            onClick={() => setClosingAll(true)}
            size="small"
          >
            Cerrar todas
          </Button>
        }
        title="Mis sesiones"
      >
        <SessionsTable
          onCloseSession={async (session) => {
            await authService.closeMySession(session.public_id);
            if (session.is_current) {
              await logout().catch(() => {});
              return;
            }
            invalidate(queryKeys.identity.me());
          }}
          sessions={sessions}
        />
      </SectionCard>

      <ChangePasswordWindow
        onClose={() => setChangingPassword(false)}
        open={changingPassword}
      />
      <ConfirmDialog
        confirmColor="error"
        confirmText="Cerrar todas"
        errorText={closeError}
        message="Se cerrará esta sesión y cualquier otra abierta en otros dispositivos."
        onClose={() => setClosingAll(false)}
        onConfirm={async () => {
          try {
            await logoutAll();
          } catch (requestError) {
            setCloseError(requestError.message);
          }
        }}
        open={closingAll}
        title="Cerrar todas las sesiones"
      />
    </>
  );
}
