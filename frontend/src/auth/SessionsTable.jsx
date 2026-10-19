import { useState } from "react";

import Button from "@mui/material/Button";

import { formatDateTime } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";
import { SectionTableArea } from "@ui/layout/SectionCard.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

/**
 * Sesiones vivas de una cuenta (riesgo A, ADR-0011): dispositivo, IP, inicio y
 * ultima actividad, con cierre de una sesion concreta. Lo usan "Mi cuenta" (las
 * propias) y la ficha de la cuenta (administracion).
 *
 * @param {object} props
 * @param {Array} props.sessions
 * @param {(session: object) => Promise<void>} [props.onCloseSession] Sin el, no se ofrece cerrar.
 */
export function SessionsTable({ onCloseSession, sessions }) {
  const [closing, setClosing] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const columns = [
    {
      key: "device",
      label: "Dispositivo",
      render: (row) => (
        <>
          {row.device}{" "}
          {row.is_current ? (
            <StatusChip label="Esta sesión" variant="primary" />
          ) : null}
        </>
      ),
    },
    {
      key: "ip_address",
      label: "Dirección IP",
      render: (row) => row.ip_address || <MutedCell>—</MutedCell>,
    },
    {
      key: "started_at",
      label: "Inicio",
      render: (row) => formatDateTime(row.started_at),
    },
    {
      key: "last_activity_at",
      label: "Última actividad",
      render: (row) => formatDateTime(row.last_activity_at),
    },
    ...(onCloseSession
      ? [
          {
            key: "actions",
            label: "Acciones",
            align: "right",
            render: (row) => (
              <Button
                color="error"
                onClick={() => setClosing(row)}
                size="small"
              >
                Cerrar sesión
              </Button>
            ),
          },
        ]
      : []),
  ];

  return (
    <>
      <SectionTableArea>
        <DataTable
          columns={columns}
          emptyMessage="Sin sesiones activas."
          getRowKey={(row) => row.public_id}
          rows={sessions ?? []}
        />
      </SectionTableArea>
      <ConfirmDialog
        busy={busy}
        confirmColor="error"
        confirmText="Cerrar sesión"
        errorText={error}
        message={
          closing?.is_current
            ? "Es la sesión que está usando: tendrá que iniciar sesión de nuevo."
            : `Se cerrará la sesión de ${closing?.device ?? "ese dispositivo"}.`
        }
        onClose={() => {
          setClosing(null);
          setError("");
        }}
        onConfirm={async () => {
          setBusy(true);
          setError("");
          try {
            await onCloseSession(closing);
            setClosing(null);
          } catch (closeError) {
            setError(closeError.message);
          } finally {
            setBusy(false);
          }
        }}
        open={Boolean(closing)}
        title="Cerrar sesión"
      />
    </>
  );
}
