import { useCallback, useState } from "react";

import Alert from "@mui/material/Alert";
import AlertTitle from "@mui/material/AlertTitle";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";

import { accountsService } from "@auth/accountsService.js";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";
import { MutedCell } from "@ui/table/cells.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";

const STATUS_VARIANT = {
  active: "success",
  pending: "warning",
  disabled: "neutral",
  blocked: "error",
};

const STATUS_LABEL = {
  active: "Activo",
  pending: "Pendiente",
  disabled: "Desactivado",
  blocked: "Bloqueado",
};

const COLUMNS = [
  {
    key: "person_name",
    label: "Persona",
    render: (row) => row.person_name || <MutedCell>Sin vincular</MutedCell>,
  },
  { key: "username", label: "Usuario" },
  {
    key: "status",
    label: "Estado",
    render: (row) => (
      <StatusChip
        label={STATUS_LABEL[row.status] ?? row.status}
        variant={STATUS_VARIANT[row.status] ?? "neutral"}
      />
    ),
  },
];

/**
 * RF-CTA-006: Pagina de administracion de cuentas.
 *
 * Lista cuentas con filtro por estado y busqueda. Permite desactivar
 * cuentas con verificacion de dependencias (asignaciones docentes vigentes).
 */
export function AccountsPage() {
  const loadAccounts = useCallback(
    (params) => accountsService.list(params),
    []
  );
  const list = usePaginatedList(loadAccounts);

  const [disabling, setDisabling] = useState(null);
  const [warnings, setWarnings] = useState(null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const [sessionTarget, setSessionTarget] = useState(null);
  const [resetLink, setResetLink] = useState("");

  const handleDisableClick = async (account) => {
    setActionError("");
    setBusy(true);
    try {
      const result = await accountsService.disable(account.id);
      if (result.disabled === false) {
        setWarnings(result.warnings);
        setDisabling(account);
      } else {
        list.refresh();
      }
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleForceDisable = async () => {
    setBusy(true);
    setActionError("");
    try {
      await accountsService.disable(disabling.id, { force: true });
      setDisabling(null);
      setWarnings(null);
      list.refresh();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const closeDialog = () => {
    setDisabling(null);
    setWarnings(null);
  };

  const closeAccountSessions = async () => {
    setBusy(true);
    setActionError("");
    try {
      await accountsService.closeSessions(sessionTarget.id);
      setSessionTarget(null);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const issuePasswordReset = async (account) => {
    setBusy(true);
    setActionError("");
    try {
      const result = await accountsService.issuePasswordReset(account.id);
      setResetLink(result.token);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader
        breadcrumb="Administracion"
        subtitle="Gestion de cuentas de usuario, estados y desactivacion."
        title="Seguridad y cuentas"
      />

      <ListSection
        actionError={actionError}
        columns={COLUMNS}
        emptyMessage="No hay cuentas registradas."
        fillHeight
        getRowKey={(account) => account.id}
        list={list}
        renderActions={(account) =>
          account.status !== "disabled" ? (
            <Stack direction="row" spacing={0.5}>
              <Button
                disabled={busy}
                onClick={() => issuePasswordReset(account)}
                size="small"
                variant="text"
              >
                Restablecer acceso
              </Button>
              <Button
                disabled={busy}
                onClick={() => setSessionTarget(account)}
                size="small"
                variant="text"
              >
                Cerrar sesiones
              </Button>
              <Button
                color="error"
                disabled={busy}
                onClick={() => handleDisableClick(account)}
                size="small"
                variant="text"
              >
                Desactivar
              </Button>
            </Stack>
          ) : null
        }
        subtitle="Cuentas de usuario"
        title="Cuentas registradas"
      />

      <Dialog maxWidth="sm" fullWidth onClose={closeDialog} open={!!warnings}>
        <DialogTitle>Advertencia de dependencias</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            <AlertTitle>Asignaciones vigentes</AlertTitle>
            La cuenta de {disabling?.person_name || disabling?.username} tiene
            asignaciones docentes activas que quedarian sin responsable.
          </Alert>
          <List dense>
            {warnings?.teaching_assignments?.map((a) => (
              <ListItem key={a.id}>
                <ListItemText
                  primary={`${a.subject__name} — Seccion ${a.section__name}`}
                />
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDialog}>Cancelar</Button>
          <Button
            color="error"
            disabled={busy}
            onClick={handleForceDisable}
            variant="contained"
          >
            {busy ? "Desactivando…" : "Desactivar de todos modos"}
          </Button>
        </DialogActions>
      </Dialog>
      <ConfirmDialog
        busy={busy}
        confirmColor="error"
        confirmText="Cerrar sesiones"
        errorText={actionError}
        message={`Se cerrarán todas las sesiones activas de ${sessionTarget?.person_name || sessionTarget?.username || "esta cuenta"}. Esta acción no desactiva la cuenta.`}
        onClose={() => setSessionTarget(null)}
        onConfirm={closeAccountSessions}
        open={Boolean(sessionTarget)}
        title="Cerrar sesiones activas"
      />
      <Dialog
        maxWidth="sm"
        fullWidth
        onClose={() => setResetLink("")}
        open={Boolean(resetLink)}
      >
        <DialogTitle>Enlace temporal de restablecimiento</DialogTitle>
        <DialogContent>
          <Alert severity="warning">
            Comparta esta clave temporal solo con la persona titular. Se muestra
            una sola vez y no revela ninguna contraseña.
          </Alert>
          <List dense>
            <ListItem>
              <ListItemText
                primary={resetLink}
                sx={{ overflowWrap: "anywhere" }}
              />
            </ListItem>
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetLink("")}>Cerrar</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
