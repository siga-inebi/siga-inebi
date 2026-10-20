import { useState } from "react";

import { cyclesService } from "@cycles/cyclesService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { formatDate, formatDateLong } from "@shared/utils/format.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";

import { AddButton } from "./common.jsx";

/**
 * Días no computables del ciclo (RF-JOR-010, docs/ux-ui.md C8): fechas que no
 * cuentan para el porcentaje de asistencia (asuetos, suspensiones). Quitar un
 * día lo desactiva y queda en la bitácora; no se borra.
 */
export function NonComputableDaysTab({ canManage, cycle }) {
  const cycleId = cycle.public_id;
  const isClosed = cycle.status === "closed";
  const canWrite = canManage && !isClosed;
  const [declaring, setDeclaring] = useState(false);
  const [removing, setRemoving] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const list = useServerList({
    queryKey: queryKeys.academics.list("non-computable-days", cycleId),
    fetchPage: (params) => cyclesService.listNonComputableDays(cycleId, params),
    urlPrefix: "dias_",
  });

  return (
    <>
      <ListSection
        action={
          canManage ? (
            <AddButton
              disabled={isClosed}
              hint="Un ciclo cerrado no admite cambios."
              label="Declarar día"
              onClick={() => setDeclaring(true)}
            />
          ) : null
        }
        columns={[
          {
            key: "day",
            label: "Fecha",
            render: (row) => formatDateLong(row.day),
          },
          { key: "reason", label: "Motivo", render: (row) => row.reason },
        ]}
        emptyMessage="Este ciclo no tiene días no computables."
        getRowKey={(row) => row.public_id}
        list={list}
        renderActions={
          canWrite
            ? (row) => (
                <ActionIconButton
                  label={`Quitar ${formatDate(row.day)}`}
                  onClick={() => {
                    setError("");
                    setRemoving(row);
                  }}
                >
                  <DeleteOutlineIcon fontSize="small" />
                </ActionIconButton>
              )
            : undefined
        }
        showInactiveToggle={false}
        subtitle={`Fechas entre ${formatDate(cycle.starts_on)} y ${formatDate(cycle.ends_on)} que no cuentan para la asistencia.`}
        title="Días no computables"
      />

      {declaring ? (
        <EntityFormWindow
          description="El día deja de contar para el porcentaje de asistencia de todo el ciclo."
          fields={[
            { name: "day", label: "Fecha", type: "date", required: true },
            {
              name: "reason",
              label: "Motivo",
              required: true,
              placeholder: "Asueto, suspensión de clases…",
            },
          ]}
          initialValues={{ day: "", reason: "" }}
          onCancel={() => setDeclaring(false)}
          onSubmit={async (values) => {
            await cyclesService.declareNonComputableDay(cycleId, values);
            setDeclaring(false);
            list.refresh();
          }}
          open
          submitLabel="Declarar día"
          title="Declarar día no computable"
        />
      ) : null}

      <ConfirmDialog
        busy={busy}
        confirmColor="error"
        confirmText="Quitar día"
        errorText={error || undefined}
        message={
          removing
            ? `El ${formatDateLong(removing.day)} vuelve a contar para la asistencia. Queda registrado en la bitácora.`
            : ""
        }
        onClose={() => {
          if (busy) return;
          setRemoving(null);
          setError("");
        }}
        onConfirm={async () => {
          setBusy(true);
          setError("");
          try {
            await cyclesService.removeNonComputableDay(removing.public_id);
            setRemoving(null);
            list.refresh();
          } catch (requestError) {
            setError(requestError.message);
          } finally {
            setBusy(false);
          }
        }}
        open={Boolean(removing)}
        title="Quitar día no computable"
      />
    </>
  );
}
