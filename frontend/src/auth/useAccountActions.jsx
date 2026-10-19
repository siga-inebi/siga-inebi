import { Suspense, useState } from "react";

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

import {
  accountsService,
  activationLink,
  passwordResetLink,
} from "@auth/accountsService.js";
import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { formatDateTime } from "@shared/utils/format.js";
import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";
import { ReasonDialog } from "@ui/feedback/ReasonDialog.jsx";

import {
  LazyEntityFormWindow as EntityFormWindow,
  LazySecretHandoverDialog as SecretHandoverDialog,
} from "./lazyAccountWindows.jsx";

const EDIT_FIELDS = [
  { name: "username", label: "Usuario", required: true },
  { name: "email", label: "Correo", type: "email" },
];

function accountName(account) {
  return account?.person_name || account?.username || "esta cuenta";
}

/**
 * Acciones administrativas sobre una cuenta, compartidas por el listado y la
 * ficha (docs/ux-ui.md U2, U3, U6, U7, U9; ADR-0011 D8).
 *
 * `actionsFor(account)` devuelve las acciones en orden fijo (consultar,
 * corregir, entregar accesos, levantar bloqueos y, al final, la destructiva)
 * y solo las que la cuenta en sesion puede ejecutar y el estado admite.
 * `dialogs` son las ventanas que esas acciones abren.
 *
 * @param {object} options
 * @param {Function} [options.onChanged] Se llama despues de cada cambio.
 * @param {Function} [options.onView] Abrir la ficha (solo en el listado).
 */
export function useAccountActions({ onChanged, onView } = {}) {
  const { can, user } = usePermissions();
  const [pending, setPending] = useState(null);
  const [secret, setSecret] = useState(null);
  const [warnings, setWarnings] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const close = () => {
    setPending(null);
    setError("");
  };
  const changed = () => onChanged?.();

  const showActivationCode = (account, result) =>
    setSecret({
      title: "Código de activación",
      secretLabel: "Código de activación",
      secret: result.activation_code,
      details: [
        { label: "Persona", value: accountName(account) },
        { label: "Usuario", value: account.username },
        { label: "Vence", value: formatDateTime(result.activation_expires_at) },
      ],
      instructions: `Ingrese a ${activationLink()} con su usuario y este código para definir su contraseña. El código es de un solo uso.`,
    });

  const issueReset = async (account) => {
    setBusy(true);
    setError("");
    try {
      const result = await accountsService.issuePasswordReset(
        account.public_id
      );
      setSecret({
        title: "Enlace de restablecimiento",
        secretLabel: "Enlace de restablecimiento",
        secret: passwordResetLink(result.token),
        details: [
          { label: "Persona", value: accountName(account) },
          { label: "Usuario", value: account.username },
          { label: "Vence", value: formatDateTime(result.expires_at) },
        ],
        instructions:
          "Abra este enlace en el navegador y defina una contraseña nueva. Es de un solo uso; al usarlo se cierran sus sesiones abiertas.",
      });
      changed();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const reissueActivation = async (account) => {
    setBusy(true);
    setError("");
    try {
      const result = await accountsService.reissueActivation(account.public_id);
      setPending(null);
      showActivationCode(account, result);
      changed();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const closeSessions = async (account) => {
    setBusy(true);
    setError("");
    try {
      await accountsService.closeSessions(account.public_id);
      setPending(null);
      changed();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const disable = async (account, reason, force = false) => {
    const result = await accountsService.disable(account.public_id, {
      force,
      reason,
    });
    if (result?.disabled === false) {
      setPending(null);
      setWarnings({ account, reason, list: result.warnings });
      return;
    }
    setPending(null);
    setWarnings(null);
    changed();
  };

  const actionsFor = (account) => {
    const disabled = account.status === "disabled";
    return [
      {
        key: "view",
        label: "Ver ficha",
        hidden: !onView,
        onClick: () => onView?.(account),
      },
      {
        key: "edit",
        label: "Editar usuario y correo",
        // D1 (ADR-0011): `account.update`, y nunca la cuenta propia (eso es Mi cuenta).
        hidden:
          !can(PERMISSION.ACCOUNT_UPDATE) ||
          account.public_id === user?.public_id,
        onClick: () => setPending({ type: "edit", account }),
      },
      {
        key: "reset",
        label: "Restablecer acceso",
        hint: "Genera un enlace de un solo uso",
        hidden: disabled || !can(PERMISSION.ACCOUNT_DISABLE),
        onClick: () => issueReset(account),
      },
      {
        key: "reissue",
        label: "Reemitir código de activación",
        hidden:
          account.status !== "pending" || !can(PERMISSION.ACCOUNT_ACTIVATE),
        onClick: () => setPending({ type: "reissue", account }),
      },
      {
        key: "unlock",
        label: "Desbloquear",
        hint: "Levanta el bloqueo por intentos fallidos",
        hidden: !account.is_locked || !can(PERMISSION.ACCOUNT_ACTIVATE),
        onClick: () => setPending({ type: "unlock", account }),
      },
      {
        key: "reactivate",
        label: "Reactivar",
        hint: "Vuelve a pendiente con un código nuevo",
        hidden: !disabled || !can(PERMISSION.ACCOUNT_ACTIVATE),
        onClick: () => setPending({ type: "reactivate", account }),
      },
      {
        key: "sessions",
        label: "Cerrar sesiones",
        hidden: disabled || !can(PERMISSION.ACCOUNT_DISABLE),
        onClick: () => setPending({ type: "sessions", account }),
      },
      {
        key: "disable",
        label: "Desactivar",
        danger: true,
        hidden: disabled || !can(PERMISSION.ACCOUNT_DISABLE),
        onClick: () => setPending({ type: "disable", account }),
      },
    ];
  };

  const account = pending?.account;
  const dialogs = (
    <>
      {error && !pending ? (
        <Alert onClose={() => setError("")} role="alert" severity="error">
          {error}
        </Alert>
      ) : null}

      {pending?.type === "edit" ? (
        <Suspense fallback={null}>
          <EntityFormWindow
            draftKey={`account-edit:${account.public_id}`}
            description="El cambio queda registrado en la bitácora con el valor anterior y el nuevo."
            fields={EDIT_FIELDS}
            initialValues={{
              username: account.username,
              email: account.email ?? "",
            }}
            onCancel={close}
            onSubmit={async (values) => {
              await accountsService.update(account.public_id, values);
              close();
              changed();
            }}
            open
            title={`Editar cuenta de ${accountName(account)}`}
          />
        </Suspense>
      ) : null}

      <ConfirmDialog
        busy={busy}
        confirmText="Reemitir código"
        errorText={error}
        message={`Se anula el código anterior de ${accountName(account)} y se emite uno nuevo.`}
        onClose={close}
        onConfirm={() => reissueActivation(account)}
        open={pending?.type === "reissue"}
        title="Reemitir código de activación"
      />

      <ConfirmDialog
        busy={busy}
        confirmColor="error"
        confirmText="Cerrar sesiones"
        errorText={error}
        message={`Se cerrarán todas las sesiones activas de ${accountName(account)}. Esta acción no desactiva la cuenta.`}
        onClose={close}
        onConfirm={() => closeSessions(account)}
        open={pending?.type === "sessions"}
        title="Cerrar sesiones activas"
      />

      <ReasonDialog
        confirmText="Desbloquear"
        message={`Se levanta el bloqueo temporal de ${accountName(account)} y se reinician sus intentos fallidos. No cambia su contraseña.`}
        onClose={close}
        onConfirm={async (reason) => {
          await accountsService.unlock(account.public_id, reason);
          close();
          changed();
        }}
        open={pending?.type === "unlock"}
        title="Desbloquear cuenta"
      />

      <ReasonDialog
        confirmText="Reactivar"
        message={`La cuenta de ${accountName(account)} vuelve a "Pendiente" con un código de activación nuevo: la persona define otra contraseña. Los roles revocados no vuelven solos; asígnelos de nuevo si corresponde.`}
        onClose={close}
        onConfirm={async (reason) => {
          const result = await accountsService.reactivate(
            account.public_id,
            reason
          );
          close();
          showActivationCode(result.account ?? account, result);
          changed();
        }}
        open={pending?.type === "reactivate"}
        title="Reactivar cuenta"
      />

      <ReasonDialog
        confirmColor="error"
        confirmText="Desactivar"
        message={`La cuenta de ${accountName(account)} deja de poder entrar. No se borra: su historia se conserva y se puede reactivar.`}
        onClose={close}
        onConfirm={(reason) => disable(account, reason)}
        open={pending?.type === "disable"}
        title="Desactivar cuenta"
      />

      <Dialog
        fullWidth
        maxWidth="sm"
        onClose={() => setWarnings(null)}
        open={Boolean(warnings)}
      >
        <DialogTitle>Advertencia de dependencias</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            <AlertTitle>Asignaciones vigentes</AlertTitle>
            La cuenta de {accountName(warnings?.account)} tiene asignaciones
            docentes activas que quedarían sin responsable.
          </Alert>
          <List dense>
            {warnings?.list?.teaching_assignments?.map((assignment) => (
              <ListItem key={assignment.public_id}>
                <ListItemText
                  primary={`${assignment.subject__name} — Sección ${assignment.section__name}`}
                />
              </ListItem>
            ))}
          </List>
          {error ? (
            <Alert role="alert" severity="error">
              {error}
            </Alert>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setWarnings(null)}>Cancelar</Button>
          <Button
            color="error"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              setError("");
              try {
                await disable(warnings.account, warnings.reason, true);
              } catch (requestError) {
                setError(requestError.message);
              } finally {
                setBusy(false);
              }
            }}
            variant="contained"
          >
            {busy ? "Desactivando…" : "Desactivar de todos modos"}
          </Button>
        </DialogActions>
      </Dialog>

      {secret ? (
        <Suspense fallback={null}>
          <SecretHandoverDialog
            details={secret?.details ?? []}
            instructions={secret?.instructions ?? ""}
            onClose={() => setSecret(null)}
            open={Boolean(secret)}
            secret={secret?.secret ?? ""}
            secretLabel={secret?.secretLabel ?? ""}
            title={secret?.title ?? ""}
          />
        </Suspense>
      ) : null}
    </>
  );

  /** Abre una accion desde fuera del menu (p.ej. "Reactivar" junto a un aviso). */
  const startAction = (type, target) => setPending({ type, account: target });

  return { actionsFor, dialogs, busy, startAction };
}
