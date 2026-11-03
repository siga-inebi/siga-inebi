import { useState } from "react";

import { CYCLE_STATUS, cyclesService } from "@cycles/cyclesService.js";
import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";
import { ReasonDialog } from "@ui/feedback/ReasonDialog.jsx";

import { CycleFormWindow } from "./CycleFormWindow.jsx";
import { nextCycleYear, revertBlockersText } from "./cyclePresentation.js";

/**
 * Acciones del ciclo de vida de un ciclo escolar, compartidas por el listado y
 * la vista de detalle (docs/ux-ui.md 2.1, ADR-0011 D1, D2, D3, D6).
 *
 * `actionsFor(cycle, context)` devuelve las acciones en orden fijo con el
 * contrato de `RowActionsMenu` (`hidden`, `disabled`, `hint`). Solo aparecen
 * las que el estado admite y la cuenta puede ejecutar; cuando una no procede
 * por una regla del backend (otro ciclo activo, borrador sin clonar, ciclo con
 * actividad) se deshabilita y dice por que, con lo que informa
 * `GET readiness/`. El backend vuelve a validar cada accion.
 *
 * @param {object} options
 * @param {Function} [options.onChanged] Despues de cada cambio.
 * @param {Function} [options.onView]    Abrir el detalle (solo en el listado).
 * @param {Function} [options.onCloned]  Recibe el ciclo creado al clonar.
 */
export function useCycleActions({ onChanged, onCloned, onView } = {}) {
  const { can } = usePermissions();
  const [pending, setPending] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const canManage = can(PERMISSION.SCOPE_ASSIGN);
  const canRevert = can(PERMISSION.ACADEMIC_CYCLE_REVERT);
  const canReopen = can(PERMISSION.ACADEMIC_CYCLE_REOPEN);

  const close = () => {
    if (busy) return;
    setPending(null);
    setError("");
  };
  const done = () => {
    setPending(null);
    setError("");
    onChanged?.();
  };

  const run = async (action) => {
    setBusy(true);
    setError("");
    try {
      await action();
      done();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  /**
   * @param {object} cycle
   * @param {object} [context]
   * @param {{public_id: string, name: string}|null} [context.activeCycle] Otro ciclo activo (D1).
   * @param {object|null} [context.readiness] Respuesta de `readiness/` del ciclo.
   */
  const actionsFor = (cycle, { activeCycle = null, readiness = null } = {}) => {
    const isDraft = cycle.status === CYCLE_STATUS.draft;
    const isActive = cycle.status === CYCLE_STATUS.active;
    const isClosed = cycle.status === CYCLE_STATUS.closed;
    const otherActive =
      activeCycle && activeCycle.public_id !== cycle.public_id
        ? activeCycle
        : null;
    const revertBlocked = readiness ? !readiness.revert?.allowed : false;

    return [
      {
        key: "view",
        label: "Ver detalle",
        hidden: !onView,
        onClick: () => onView?.(cycle),
      },
      {
        key: "edit",
        label: "Editar",
        hidden: !isDraft || !canManage,
        onClick: () => setPending({ kind: "edit", cycle }),
      },
      {
        key: "activate",
        label: "Activar",
        hidden: !isDraft || !canManage,
        disabled: Boolean(otherActive),
        hint: otherActive
          ? `Cierre primero el ciclo «${otherActive.name}».`
          : undefined,
        onClick: () => setPending({ kind: "activate", cycle }),
      },
      {
        key: "clone",
        label: "Clonar estructura",
        hidden: !canManage,
        disabled: isDraft,
        hint: isDraft
          ? "Un borrador no se clona: actívelo o ciérrelo antes."
          : undefined,
        onClick: () => setPending({ kind: "clone", cycle }),
      },
      {
        key: "close",
        label: "Cerrar ciclo",
        hidden: !isActive || !canManage,
        onClick: () => setPending({ kind: "close", cycle }),
      },
      {
        key: "revert",
        label: "Volver a borrador",
        hidden: !isActive || !canRevert,
        disabled: revertBlocked,
        hint: revertBlocked ? revertBlockersText(readiness) : undefined,
        onClick: () => setPending({ kind: "revert", cycle }),
      },
      {
        key: "reopen",
        label: "Reabrir",
        hidden: !isClosed || !canReopen,
        onClick: () => setPending({ kind: "reopen", cycle }),
      },
    ];
  };

  const cycle = pending?.cycle;
  const dialogs = (
    <>
      {pending?.kind === "edit" ? (
        <CycleFormWindow
          description="Solo un ciclo en borrador se puede editar. Cambiar el año vuelve a proponer el nombre y las fechas."
          initialValues={cycle}
          key={`edit-${cycle.public_id}`}
          onCancel={close}
          onSubmit={async (payload) => {
            await cyclesService.update(cycle.public_id, payload);
            done();
          }}
          submitLabel="Guardar cambios"
          title={`Editar ${cycle.name}`}
        />
      ) : null}

      {pending?.kind === "clone" ? (
        <CycleFormWindow
          description={`Se copiará la estructura académica de «${cycle.name}» (oferta de grados, secciones y plan de estudios) a un ciclo nuevo en borrador. Las asignaciones docentes solo si lo pide; se copian únicamente las vigentes.`}
          initialYear={nextCycleYear(cycle)}
          key={`clone-${cycle.public_id}`}
          onCancel={close}
          onSubmit={async (payload) => {
            const created = await cyclesService.clone(cycle.public_id, payload);
            done();
            onCloned?.(created);
          }}
          submitLabel="Clonar estructura"
          title={`Clonar ${cycle.name}`}
          withAssignmentsToggle
        />
      ) : null}

      <ConfirmDialog
        busy={busy}
        confirmText={busy ? "Activando…" : "Sí, activar"}
        errorText={
          pending?.kind === "activate" ? error || undefined : undefined
        }
        message={
          cycle
            ? `«${cycle.name}» pasará a ser el ciclo vigente: admite matrícula, asistencia y evaluación, y su estructura (secciones y plan de estudios) deja de editarse. Si le falta algo para activarse, el sistema lo indica y el ciclo sigue en borrador.`
            : ""
        }
        onClose={close}
        onConfirm={() => run(() => cyclesService.activate(cycle.public_id))}
        open={pending?.kind === "activate"}
        title="Activar ciclo escolar"
      />

      <ConfirmDialog
        busy={busy}
        confirmColor="error"
        confirmText={busy ? "Cerrando…" : "Sí, cerrar ciclo"}
        errorText={pending?.kind === "close" ? error || undefined : undefined}
        message={
          cycle
            ? `Se cerrará «${cycle.name}»: sus resultados finales y la condición de promoción quedan congelados y el ciclo deja de aceptar escrituras. Requiere que todas las unidades de evaluación estén cerradas y que las ventanas de recuperación hayan vencido.`
            : ""
        }
        onClose={close}
        onConfirm={() => run(() => cyclesService.close(cycle.public_id))}
        open={pending?.kind === "close"}
        title="Cerrar ciclo escolar"
      />

      <ReasonDialog
        confirmColor="warning"
        confirmText="Volver a borrador"
        message={
          cycle
            ? `«${cycle.name}» deja de ser el ciclo vigente y su estructura se puede corregir otra vez. Se conservan secciones, plan de estudios y asignaciones docentes. Solo procede si el ciclo no tiene matrículas, notas, asistencia, unidades cerradas ni documentos emitidos.`
            : ""
        }
        onClose={close}
        onConfirm={async (reason) => {
          await cyclesService.revertToDraft(cycle.public_id, reason);
          done();
        }}
        open={pending?.kind === "revert"}
        title="Volver a borrador"
      />

      <ReasonDialog
        confirmText="Reabrir ciclo"
        message={
          cycle
            ? `«${cycle.name}» vuelve a estar activo y acepta escrituras otra vez. El motivo queda en la bitácora.`
            : ""
        }
        onClose={close}
        onConfirm={async (reason) => {
          await cyclesService.reopen(cycle.public_id, reason);
          done();
        }}
        open={pending?.kind === "reopen"}
        title="Reabrir ciclo"
      />
    </>
  );

  return { actionsFor, dialogs };
}
