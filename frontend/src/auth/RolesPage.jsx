import { useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";

import { ASSIGNMENT_STATUS_LABEL } from "@auth/accountLabels.js";
import { groupPermissions, rolesService } from "@auth/rolesService.js";
import { useAuth } from "@auth/useAuth.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { formatDate } from "@shared/utils/format.js";
import { RowActionsMenu } from "@ui/buttons/RowActionsMenu.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { ReasonDialog } from "@ui/feedback/ReasonDialog.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

import { RoleEditorWindow } from "./RoleEditorWindow.jsx";
import { TextLink } from "@ui/display/TextLink.jsx";

const HOLDER_COLUMNS = [
  {
    key: "person_name",
    label: "Persona",
    render: (row) => (
      <TextLink to={`/app/cuentas/${row.account}`}>
        {row.person_name || row.username}
      </TextLink>
    ),
  },
  { key: "username", label: "Usuario" },
  { key: "role_name", label: "Por el rol" },
  {
    key: "ends_at",
    label: "Hasta",
    render: (row) =>
      row.ends_at ? (
        formatDate(row.ends_at)
      ) : (
        <MutedCell>Sin vencimiento</MutedCell>
      ),
  },
  {
    key: "status",
    label: "Estado",
    render: (row) => ASSIGNMENT_STATUS_LABEL[row.status] ?? row.status,
  },
];

/** RO5: quien tiene un rol vigente. */
function RoleHoldersWindow({ onClose, role }) {
  const { data, loading } = useResourceQuery(
    queryKeys.identity.roleHolders(role.public_id),
    () => rolesService.holders(role.public_id, { page_size: 100 })
  );
  return (
    <FloatingWindow
      onClose={onClose}
      open
      title={`Quién tiene el rol «${role.name}»`}
      width={WINDOW_WIDTH.wide}
    >
      <DataTable
        columns={HOLDER_COLUMNS}
        emptyMessage="Nadie tiene este rol vigente."
        getRowKey={(row) => row.assignment}
        loading={loading}
        rows={data?.results ?? []}
      />
    </FloatingWindow>
  );
}

/** RO5: "quien tiene este permiso", util para auditorias de acceso. */
function PermissionHoldersWindow({ onClose, permissions }) {
  const [code, setCode] = useState("");
  const { data, loading } = useResourceQuery(
    queryKeys.identity.permissionHolders(code),
    () => rolesService.permissionHolders(code, { page_size: 100 }),
    { enabled: Boolean(code) }
  );
  return (
    <FloatingWindow
      onClose={onClose}
      open
      title="¿Quién tiene un permiso?"
      width={WINDOW_WIDTH.wide}
    >
      <Stack gap={2}>
        <FormSelect
          fullWidth
          label="Permiso"
          name="permission"
          onChange={(event) => setCode(event.target.value)}
          options={permissions.map((permission) => ({
            value: permission.code,
            label: `${permission.group_label} · ${permission.name}`,
          }))}
          placeholder="Seleccione un permiso"
          value={code}
        />
        {code ? (
          <DataTable
            columns={HOLDER_COLUMNS}
            emptyMessage="Ninguna cuenta tiene este permiso vigente."
            getRowKey={(row) => row.assignment}
            loading={loading}
            rows={data?.results ?? []}
          />
        ) : null}
      </Stack>
    </FloatingWindow>
  );
}

/** RO5: comparacion de roles por permiso. */
function CompareRolesWindow({ onClose, permissions, roles }) {
  // Hasta que la persona elija, se comparan los dos primeros roles (que pueden
  // llegar despues de abrir la ventana).
  const [picked, setPicked] = useState(null);
  const chosen = picked ?? roles.slice(0, 2).map((role) => role.public_id);
  const selectedRoles = roles.filter((role) => chosen.includes(role.public_id));
  const groups = useMemo(() => groupPermissions(permissions), [permissions]);
  const toggle = (id) =>
    setPicked(
      chosen.includes(id)
        ? chosen.filter((value) => value !== id)
        : [...chosen, id]
    );

  return (
    <FloatingWindow
      onClose={onClose}
      open
      title="Comparar roles"
      width={WINDOW_WIDTH.wide}
    >
      <Stack gap={2}>
        <Stack direction="row" flexWrap="wrap" gap={1}>
          {roles.map((role) => (
            <FormControlLabel
              control={
                <Checkbox
                  checked={chosen.includes(role.public_id)}
                  onChange={() => toggle(role.public_id)}
                  size="small"
                />
              }
              key={role.public_id}
              label={role.name}
            />
          ))}
        </Stack>
        {selectedRoles.length === 0 ? (
          <Typography color="text.secondary" variant="body2">
            Elija al menos un rol.
          </Typography>
        ) : (
          <Box sx={{ overflowX: "auto" }}>
            <Table aria-label="Comparación de roles" size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Permiso</TableCell>
                  {selectedRoles.map((role) => (
                    <TableCell align="center" key={role.public_id}>
                      {role.name}
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {groups.flatMap((group) => [
                  <TableRow key={`group-${group.key}`}>
                    <TableCell colSpan={selectedRoles.length + 1}>
                      <Typography fontWeight={600} variant="caption">
                        {group.label}
                      </Typography>
                    </TableCell>
                  </TableRow>,
                  ...group.permissions.map((permission) => (
                    <TableRow key={permission.code}>
                      <TableCell>{permission.name}</TableCell>
                      {selectedRoles.map((role) => (
                        <TableCell align="center" key={role.public_id}>
                          {role.permissions.includes(permission.code)
                            ? "Sí"
                            : "—"}
                        </TableCell>
                      ))}
                    </TableRow>
                  )),
                ])}
              </TableBody>
            </Table>
          </Box>
        )}
      </Stack>
    </FloatingWindow>
  );
}

/**
 * Roles y permisos (docs/ux-ui.md 2.17.4, RO1-RO6).
 *
 * Listado con cuantas cuentas tiene cada rol; editor con permisos agrupados y
 * traducidos; roles del sistema marcados y protegidos; comparacion de roles y
 * "quien tiene este permiso"; retiro seguro de un rol sin uso (no se borra).
 */
export function RolesPage() {
  const { user } = useAuth();
  const [editing, setEditing] = useState(null);
  const [holdersOf, setHoldersOf] = useState(null);
  const [retiring, setRetiring] = useState(null);
  const [comparing, setComparing] = useState(false);
  const [permissionLookup, setPermissionLookup] = useState(false);

  const list = useServerList({
    queryKey: [...queryKeys.identity.all, "roles-list"],
    fetchPage: rolesService.listPage,
    defaultFilters: { include_inactive: "false" },
    defaultPageSize: 50,
  });
  const { data: permissions } = useResourceQuery(
    queryKeys.identity.permissions(),
    () => rolesService.permissions(),
    { defaultData: [] }
  );
  const { data: allRoles } = useResourceQuery(
    queryKeys.identity.roles({ scope: "compare" }),
    () => rolesService.listAll({ include_inactive: "false" }),
    { defaultData: [], enabled: comparing }
  );

  const save = async (values) => {
    if (editing?.role) {
      await rolesService.update(editing.role.public_id, values);
    } else {
      await rolesService.create(values);
    }
    setEditing(null);
  };

  const columns = [
    {
      key: "name",
      label: "Rol",
      render: (row) => (
        <Stack direction="row" alignItems="center" flexWrap="wrap" gap={0.75}>
          <span>{row.name}</span>
          {row.is_system ? (
            <StatusChip label="Del sistema" variant="purple" />
          ) : null}
          {!row.is_active ? (
            <StatusChip label="Retirado" variant="neutral" />
          ) : null}
        </Stack>
      ),
    },
    {
      key: "description",
      label: "Descripción",
      render: (row) =>
        row.description || <MutedCell>Sin descripción</MutedCell>,
    },
    {
      key: "active_account_count",
      label: "Cuentas",
      align: "right",
      render: (row) => String(row.active_account_count ?? 0),
    },
    {
      key: "permissions",
      label: "Permisos",
      align: "right",
      render: (row) => String(row.permissions.length),
    },
    {
      key: "session_idle_timeout_minutes",
      label: "Inactividad",
      align: "right",
      render: (row) => `${row.session_idle_timeout_minutes} min`,
    },
  ];

  return (
    <>
      <PageHeader
        action={
          <Stack direction="row" flexWrap="wrap" gap={1}>
            <Button
              onClick={() => setPermissionLookup(true)}
              variant="outlined"
            >
              ¿Quién tiene un permiso?
            </Button>
            <Button onClick={() => setComparing(true)} variant="outlined">
              Comparar roles
            </Button>
            <Button
              onClick={() => setEditing({ role: null })}
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Nuevo rol
            </Button>
          </Stack>
        }
        breadcrumb="Administración"
        subtitle="Un rol agrupa permisos. Se asigna a una cuenta con un alcance y una vigencia desde la ficha de la cuenta."
        title="Roles"
      />

      <ListSection
        columns={columns}
        emptyMessage="No hay roles registrados."
        fillHeight
        filters={
          <Stack direction="row" sx={{ px: { xs: 1.5, md: 2 }, py: 1 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={list.filters.include_inactive === "true"}
                  onChange={(event) =>
                    list.setFilter(
                      "include_inactive",
                      event.target.checked ? "true" : "false"
                    )
                  }
                  size="small"
                />
              }
              label="Mostrar retirados"
            />
          </Stack>
        }
        getRowKey={(role) => role.public_id}
        list={list}
        onRowClick={(role) => setEditing({ role })}
        renderActions={(role) => (
          <RowActionsMenu
            actions={[
              {
                key: "edit",
                label: "Editar",
                onClick: () => setEditing({ role }),
              },
              {
                key: "holders",
                label: "Ver quién lo tiene",
                onClick: () => setHoldersOf(role),
              },
              {
                key: "retire",
                label: "Retirar rol",
                hint: "Solo si nadie lo tiene vigente",
                danger: true,
                hidden: !role.is_active || role.is_system,
                onClick: () => setRetiring({ role, action: "retire" }),
              },
              {
                key: "reactivate",
                label: "Volver a ofrecer",
                hidden: role.is_active,
                onClick: () => setRetiring({ role, action: "reactivate" }),
              },
            ]}
            label={role.name}
          />
        )}
        showInactiveToggle={false}
        title="Roles"
      />

      {editing ? (
        <RoleEditorWindow
          canEditSystem={Boolean(user?.is_superuser)}
          onClose={() => setEditing(null)}
          onSubmit={save}
          open
          permissions={permissions}
          role={editing.role}
        />
      ) : null}
      {holdersOf ? (
        <RoleHoldersWindow
          onClose={() => setHoldersOf(null)}
          role={holdersOf}
        />
      ) : null}
      {comparing ? (
        <CompareRolesWindow
          onClose={() => setComparing(false)}
          permissions={permissions}
          roles={allRoles}
        />
      ) : null}
      {permissionLookup ? (
        <PermissionHoldersWindow
          onClose={() => setPermissionLookup(false)}
          permissions={permissions}
        />
      ) : null}

      <ReasonDialog
        confirmColor={retiring?.action === "retire" ? "error" : "primary"}
        confirmText={
          retiring?.action === "retire" ? "Retirar" : "Volver a ofrecer"
        }
        message={
          retiring?.action === "retire"
            ? `«${retiring?.role.name}» dejará de ofrecerse al asignar roles. No se borra: su historia se conserva. Si alguien lo tiene vigente, revoque antes esas asignaciones.`
            : `«${retiring?.role.name}» vuelve a ofrecerse. Las asignaciones revocadas no vuelven solas.`
        }
        onClose={() => setRetiring(null)}
        onConfirm={async (reason) => {
          if (retiring.action === "retire") {
            await rolesService.deactivate(retiring.role.public_id, reason);
          } else {
            await rolesService.reactivate(retiring.role.public_id, reason);
          }
          setRetiring(null);
        }}
        open={Boolean(retiring)}
        title={
          retiring?.action === "retire"
            ? "Retirar rol"
            : "Volver a ofrecer el rol"
        }
      />
    </>
  );
}
