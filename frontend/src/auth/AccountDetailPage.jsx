import { lazy, Suspense, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Tooltip from "@mui/material/Tooltip";
import Stack from "@mui/material/Stack";

import {
  ACCOUNT_STATUS_VARIANT,
  ASSIGNMENT_STATUS_LABEL,
  ASSIGNMENT_STATUS_VARIANT,
  accountStatusLabel,
  auditActionLabel,
} from "@auth/accountLabels.js";
import { accountsService } from "@auth/accountsService.js";
import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { useInvalidate } from "@shared/api/invalidation.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";
import { formatDateTime } from "@shared/utils/format.js";
import { RowActionsMenu } from "@ui/buttons/RowActionsMenu.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";
import { DetailField } from "@ui/layout/DetailWindow.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

import { SessionsTable } from "./SessionsTable.jsx";

// El asistente solo se descarga al abrirlo (riesgo C).
const AssignRoleWizard = lazy(() =>
  import("./AssignRoleWizard.jsx").then((module) => ({
    default: module.AssignRoleWizard,
  }))
);

/** Regla de identidad (ADR-0011): una cuenta desactivada no recibe roles. */
const DISABLED_ROLE_HINT = "Reactive la cuenta antes de asignarle roles.";
import { scopeDimensionsText } from "./scopeChoice.js";
import { useAccountActions } from "./useAccountActions.jsx";
import { TextLink } from "@ui/display/TextLink.jsx";

function DetailGrid({ children }) {
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

/**
 * Ficha de la cuenta (docs/ux-ui.md U5): persona vinculada, estado, roles con
 * alcances y vigencias, sesiones activas e historial de accesos desde la
 * bitacora. Desde aqui se asignan y revocan roles (RA2, RA3) y se ejecutan
 * las acciones de la cuenta, incluidas reactivar y desbloquear (D8).
 */
export function AccountDetailPage() {
  const { accountId } = useParams();
  const { can } = usePermissions();
  const invalidate = useInvalidate();
  const [assigning, setAssigning] = useState(false);
  const [revoking, setRevoking] = useState(null);
  const [revokeError, setRevokeError] = useState("");
  const [revokeBusy, setRevokeBusy] = useState(false);

  const detail = useResourceQuery(queryKeys.identity.account(accountId), () =>
    accountsService.get(accountId)
  );
  const canManageRoles = can(PERMISSION.ROLE_ASSIGN);
  const assignments = useResourceQuery(
    queryKeys.identity.accountAssignments(accountId),
    () => accountsService.assignments(accountId, { page_size: 100 }),
    { enabled: canManageRoles }
  );

  const refresh = () => invalidate(queryKeys.identity.all);
  const { actionsFor, dialogs, startAction } = useAccountActions({
    onChanged: refresh,
  });

  const account = detail.data;

  if (detail.error) {
    return (
      <>
        <PageHeader
          breadcrumb="Administración · Cuentas"
          title="Ficha de la cuenta"
        />
        <Alert role="alert" severity="error">
          {detail.error}
        </Alert>
        <Button component={RouterLink} to="/app/cuentas">
          Volver a cuentas
        </Button>
      </>
    );
  }

  if (!account) {
    return (
      <PageHeader
        breadcrumb="Administración · Cuentas"
        title="Cargando cuenta…"
      />
    );
  }

  const revoke = async () => {
    setRevokeBusy(true);
    setRevokeError("");
    try {
      await accountsService.revokeAssignment(revoking.public_id);
      setRevoking(null);
      refresh();
    } catch (error) {
      setRevokeError(error.message);
    } finally {
      setRevokeBusy(false);
    }
  };

  const assignmentColumns = [
    { key: "role_name", label: "Rol" },
    {
      key: "scopes",
      label: "Alcance",
      render: (row) =>
        row.scopes.length ? (
          row.scopes.map((scope) => (
            <div key={scope.public_id}>{scopeDimensionsText(scope)}</div>
          ))
        ) : (
          <MutedCell>Sin alcance</MutedCell>
        ),
    },
    {
      key: "starts_at",
      label: "Desde",
      render: (row) => formatDateTime(row.starts_at),
    },
    {
      key: "ends_at",
      label: "Hasta",
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
          label={row.status_display ?? ASSIGNMENT_STATUS_LABEL[row.status]}
          variant={ASSIGNMENT_STATUS_VARIANT[row.status] ?? "neutral"}
        />
      ),
    },
    {
      key: "actions",
      label: "Acciones",
      align: "right",
      render: (row) =>
        row.status !== "ended" ? (
          <Button color="error" onClick={() => setRevoking(row)} size="small">
            Revocar
          </Button>
        ) : null,
    },
  ];

  const activityColumns = [
    {
      key: "created_at",
      label: "Fecha",
      render: (row) => formatDateTime(row.created_at),
    },
    {
      key: "action",
      label: "Evento",
      render: (row) => auditActionLabel(row.action),
    },
    {
      key: "actor_label",
      label: "Por",
      render: (row) =>
        row.actor_label || <MutedCell>Sistema o anónimo</MutedCell>,
    },
    {
      key: "result",
      label: "Resultado",
      render: (row) =>
        row.result === "denied" ? (
          <StatusChip label="Rechazado" variant="danger" />
        ) : (
          <StatusChip label="Correcto" variant="success" />
        ),
    },
    {
      key: "ip_address",
      label: "Dirección IP",
      render: (row) => row.ip_address || <MutedCell>—</MutedCell>,
    },
  ];

  return (
    <>
      <PageHeader
        action={
          <RowActionsMenu
            actions={actionsFor(account)}
            label={account.username}
          />
        }
        breadcrumb={
          <TextLink to="/app/cuentas">Administración · Cuentas</TextLink>
        }
        subtitle={account.username}
        title={account.person_name || account.username}
      />
      {dialogs}

      <SectionCard title="Datos de la cuenta">
        <DetailGrid>
          <DetailField
            label="Estado"
            value={
              <Stack direction="row" gap={0.5} flexWrap="wrap">
                <StatusChip
                  label={accountStatusLabel(account)}
                  variant={ACCOUNT_STATUS_VARIANT[account.status] ?? "neutral"}
                />
                {account.is_locked ? (
                  <StatusChip
                    label={`Bloqueada hasta ${formatDateTime(account.locked_until)}`}
                    variant="danger"
                  />
                ) : null}
              </Stack>
            }
          />
          <DetailField
            label="Persona vinculada"
            value={account.person?.full_name}
          />
          <DetailField label="Correo" value={account.email} />
          <DetailField label="Usuario" value={account.username} />
          <DetailField
            label="Creada"
            value={formatDateTime(account.date_joined)}
          />
          <DetailField
            label="Último acceso"
            value={
              account.last_login ? formatDateTime(account.last_login) : "Nunca"
            }
          />
          <DetailField
            label="Intentos fallidos"
            value={String(account.failed_login_attempts ?? 0)}
          />
          {account.status === "pending" ? (
            <DetailField
              label="Código de activación vence"
              value={
                account.activation_expires_at
                  ? formatDateTime(account.activation_expires_at)
                  : "Sin código vigente: reemítalo desde Acciones"
              }
            />
          ) : null}
        </DetailGrid>
      </SectionCard>

      {canManageRoles ? (
        <SectionCard
          action={
            <Tooltip
              title={account.status === "disabled" ? DISABLED_ROLE_HINT : ""}
            >
              <span>
                <Button
                  disabled={account.status === "disabled"}
                  onClick={() => setAssigning(true)}
                  size="small"
                  variant="contained"
                >
                  Asignar rol
                </Button>
              </span>
            </Tooltip>
          }
          subtitle="Un rol solo da permisos dentro de su alcance y su vigencia."
          title="Roles y alcances"
        >
          {account.status === "disabled" ? (
            <Alert
              action={
                can(PERMISSION.ACCOUNT_ACTIVATE) ? (
                  <Button
                    color="inherit"
                    onClick={() => startAction("reactivate", account)}
                    size="small"
                  >
                    Reactivar
                  </Button>
                ) : null
              }
              severity="info"
              sx={{ mx: 2, mt: 1.5 }}
            >
              {DISABLED_ROLE_HINT}
            </Alert>
          ) : null}
          <SectionTableArea>
            <DataTable
              columns={assignmentColumns}
              emptyMessage="Sin roles asignados."
              getRowKey={(row) => row.public_id}
              loading={assignments.loading}
              rows={assignments.data?.results ?? []}
            />
          </SectionTableArea>
        </SectionCard>
      ) : null}

      <SectionCard
        subtitle="Sesiones abiertas en este momento."
        title="Sesiones activas"
      >
        <SessionsTable
          onCloseSession={
            can(PERMISSION.ACCOUNT_DISABLE)
              ? async (session) => {
                  await accountsService.closeSession(
                    account.public_id,
                    session.public_id
                  );
                  refresh();
                }
              : undefined
          }
          sessions={account.sessions}
        />
      </SectionCard>

      <SectionCard
        subtitle="Últimos accesos y cambios, desde la bitácora."
        title="Historial de accesos"
      >
        <SectionTableArea>
          <DataTable
            columns={activityColumns}
            emptyMessage="Sin actividad registrada."
            getRowKey={(row) => `${row.created_at}-${row.action}`}
            rows={account.recent_activity ?? []}
          />
        </SectionTableArea>
      </SectionCard>

      {assigning ? (
        <Suspense fallback={null}>
          <AssignRoleWizard
            account={account}
            onAssigned={refresh}
            onClose={() => setAssigning(false)}
            open
          />
        </Suspense>
      ) : null}

      <ConfirmDialog
        busy={revokeBusy}
        confirmColor="error"
        confirmText="Revocar"
        errorText={revokeError}
        message={`Se termina hoy la vigencia de «${revoking?.role_name}». La asignación queda en el historial.`}
        onClose={() => {
          setRevoking(null);
          setRevokeError("");
        }}
        onConfirm={revoke}
        open={Boolean(revoking)}
        title="Revocar asignación de rol"
      />
    </>
  );
}
