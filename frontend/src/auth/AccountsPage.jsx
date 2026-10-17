import { lazy, Suspense, useState } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import FormControlLabel from "@mui/material/FormControlLabel";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import PersonAddAlt1OutlinedIcon from "@mui/icons-material/PersonAddAlt1Outlined";

import {
  ACCOUNT_STATUS_OPTIONS,
  ACCOUNT_STATUS_VARIANT,
  accountStatusLabel,
} from "@auth/accountLabels.js";
import { accountsService } from "@auth/accountsService.js";
import { PERMISSION } from "@auth/permissions.js";
import { rolesService } from "@auth/rolesService.js";
import { usePermissions } from "@auth/usePermissions.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { formatDate, formatDateTime } from "@shared/utils/format.js";
import { RowActionsMenu } from "@ui/buttons/RowActionsMenu.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

import { useAccountActions } from "./useAccountActions.jsx";

// "Dar acceso" se descarga al abrirlo (buscador remoto y entrega del codigo).
const GrantAccessWindow = lazy(() =>
  import("./GrantAccessWindow.jsx").then((module) => ({
    default: module.GrantAccessWindow,
  }))
);
import { TextLink } from "@ui/display/TextLink.jsx";

const EXPIRING_DAYS = 15;

function RolesCell({ roles }) {
  if (!roles?.length) return <MutedCell>Sin roles vigentes</MutedCell>;
  return (
    <Stack direction="row" flexWrap="wrap" gap={0.5}>
      {roles.map((role) => (
        <StatusChip key={role.public_id} label={role.name} variant="primary" />
      ))}
    </Stack>
  );
}

function StatusCell({ account }) {
  return (
    <Stack direction="row" flexWrap="wrap" gap={0.5}>
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
  );
}

/** RA5: asignaciones por vencer o vencidas, para que nadie pierda acceso sin aviso. */
function ExpiringAssignmentsAlert() {
  const [open, setOpen] = useState(false);
  const { data } = useResourceQuery(
    queryKeys.identity.expiring(EXPIRING_DAYS),
    () =>
      accountsService.expiringAssignments({
        days: EXPIRING_DAYS,
        page_size: 100,
      })
  );
  const rows = data?.results ?? [];
  if (rows.length === 0) return null;
  const expired = rows.filter((row) => row.status === "ended").length;
  const upcoming = rows.length - expired;

  return (
    <Alert
      action={
        <Button
          color="inherit"
          onClick={() => setOpen((value) => !value)}
          size="small"
        >
          {open ? "Ocultar" : "Ver detalle"}
        </Button>
      }
      severity="warning"
      variant="outlined"
    >
      {upcoming > 0
        ? `${upcoming} asignación(es) de rol vencen en los próximos ${EXPIRING_DAYS} días. `
        : ""}
      {expired > 0 ? `${expired} venció(eron) en los últimos 30 días.` : ""}
      {open ? (
        <List dense>
          {rows.map((row) => (
            <ListItem disableGutters key={row.assignment}>
              <ListItemText
                primary={
                  <TextLink to={`/app/cuentas/${row.account}`}>
                    {row.person_name || row.username}
                  </TextLink>
                }
                secondary={`${row.role_name} · ${row.status === "ended" ? "venció" : "vence"} el ${formatDate(row.ends_at)}`}
              />
            </ListItem>
          ))}
        </List>
      ) : null}
    </Alert>
  );
}

/**
 * Administracion de cuentas (docs/ux-ui.md 2.17.3).
 *
 * Listado paginado en el servidor con buscador (usuario, nombre, correo),
 * filtros por estado, rol y bloqueo temporal, columnas de correo, roles,
 * ultimo acceso y bloqueo (U4); acciones en un menu por fila (U9); "Dar
 * acceso al sistema" (U1) y aviso de asignaciones por vencer (RA5).
 */
export function AccountsPage() {
  const navigate = useNavigate();
  const { can } = usePermissions();
  const [granting, setGranting] = useState(false);

  const list = useServerList({
    queryKey: [...queryKeys.identity.all, "accounts"],
    fetchPage: accountsService.list,
    defaultFilters: { status: "", role: "", locked: "" },
  });

  const canSeeRoles = can(PERMISSION.ROLE_ASSIGN);
  const { data: roles } = useResourceQuery(
    queryKeys.identity.roles({ scope: "filter" }),
    () => rolesService.listAll(),
    { enabled: canSeeRoles, defaultData: [] }
  );

  const openAccount = (account) =>
    navigate(`/app/cuentas/${account.public_id}`);
  const { actionsFor, dialogs } = useAccountActions({
    onChanged: list.refresh,
    onView: openAccount,
  });

  const columns = [
    {
      key: "person_name",
      label: "Persona",
      render: (row) =>
        row.person_name ? (
          <TextLink
            onClick={(event) => event.stopPropagation()}
            to={`/app/cuentas/${row.public_id}`}
          >
            {row.person_name}
          </TextLink>
        ) : (
          <MutedCell>Sin vincular</MutedCell>
        ),
    },
    { key: "username", label: "Usuario" },
    {
      key: "email",
      label: "Correo",
      render: (row) => row.email || <MutedCell>Sin correo</MutedCell>,
    },
    {
      key: "roles",
      label: "Roles",
      render: (row) => <RolesCell roles={row.roles} />,
    },
    {
      key: "status",
      label: "Estado",
      render: (row) => <StatusCell account={row} />,
    },
    {
      key: "last_login",
      label: "Último acceso",
      render: (row) =>
        row.last_login ? (
          formatDateTime(row.last_login)
        ) : (
          <MutedCell>Nunca</MutedCell>
        ),
    },
  ];

  const hasFilters = Boolean(
    list.search ||
    list.filters.status ||
    list.filters.role ||
    list.filters.locked
  );

  return (
    <>
      <PageHeader
        action={
          can(PERMISSION.ACCOUNT_CREATE) ? (
            <Button
              onClick={() => setGranting(true)}
              startIcon={<PersonAddAlt1OutlinedIcon fontSize="small" />}
              variant="contained"
            >
              Dar acceso al sistema
            </Button>
          ) : null
        }
        breadcrumb="Administración"
        subtitle="Quién puede entrar al sistema, con qué roles y en qué estado está cada cuenta."
        title="Cuentas"
      />

      {canSeeRoles ? <ExpiringAssignmentsAlert /> : null}
      {dialogs}

      <ListSection
        columns={columns}
        emptyMessage={
          hasFilters
            ? "Sin cuentas para los filtros seleccionados."
            : "No hay cuentas registradas."
        }
        fillHeight
        filters={
          <FilterBar
            onClear={
              hasFilters
                ? () => {
                    list.setSearch("");
                    list.setFilters({ status: "", role: "", locked: "" });
                  }
                : undefined
            }
          >
            <SearchField
              debounceMs={0}
              onChange={list.setSearch}
              placeholder="Buscar por usuario, nombre o correo"
              value={list.search}
            />
            <FilterSelect
              emptyLabel="Todos los estados"
              label="Estado"
              onChange={(value) => list.setFilter("status", value)}
              options={ACCOUNT_STATUS_OPTIONS}
              value={list.filters.status}
            />
            {canSeeRoles ? (
              <FilterSelect
                emptyLabel="Todos los roles"
                label="Rol"
                onChange={(value) => list.setFilter("role", value)}
                options={roles.map((role) => ({
                  value: role.public_id,
                  label: role.name,
                }))}
                value={list.filters.role}
              />
            ) : null}
            <FormControlLabel
              control={
                <Switch
                  checked={list.filters.locked === "true"}
                  onChange={(event) =>
                    list.setFilter("locked", event.target.checked ? "true" : "")
                  }
                  size="small"
                />
              }
              label="Solo bloqueadas temporalmente"
            />
          </FilterBar>
        }
        getRowKey={(account) => account.public_id}
        list={list}
        onRowClick={openAccount}
        renderActions={(account) => (
          <RowActionsMenu
            actions={actionsFor(account)}
            label={account.username}
          />
        )}
        showInactiveToggle={false}
        subtitle="Clic en una fila para abrir la ficha de la cuenta."
        title="Cuentas registradas"
      />

      {granting ? (
        <Suspense fallback={null}>
          <GrantAccessWindow
            onClose={() => setGranting(false)}
            onCreated={() => list.refresh()}
            open
          />
        </Suspense>
      ) : null}
    </>
  );
}
