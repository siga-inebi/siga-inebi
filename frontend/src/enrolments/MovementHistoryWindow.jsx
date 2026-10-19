import { useCallback, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";

import { PAGE_SIZE } from "@academics/academicsService.js";
import {
  MOVEMENT_TYPE_LABEL,
  MOVEMENT_TYPE_VARIANT,
  enrolmentsService,
} from "@enrolments/enrolmentsService.js";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDate, formatDateTime } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { MutedCell } from "@ui/table/cells.jsx";
import { MovementForm } from "./MovementForm.jsx";

const COLUMNS = [
  {
    key: "movement_type",
    label: "Movimiento",
    render: (row) => (
      <StatusChip
        label={MOVEMENT_TYPE_LABEL[row.movement_type] ?? row.movement_type}
        variant={MOVEMENT_TYPE_VARIANT[row.movement_type] ?? "neutral"}
      />
    ),
  },
  {
    key: "effective_on",
    label: "Vigente desde",
    render: (row) => formatDate(row.effective_on),
  },
  {
    key: "created_at",
    label: "Registrado el",
    render: (row) => formatDateTime(row.created_at),
  },
  {
    key: "reason",
    label: "Motivo",
    render: (row) => row.reason || <MutedCell>Sin detalle</MutedCell>,
  },
  {
    key: "annulment",
    label: "Estado",
    render: (row) =>
      row.annulment ? (
        <Stack gap={0.5}>
          <StatusChip label="Anulado" variant="neutral" />
          <Typography variant="caption">{row.annulment.reason}</Typography>
          <Typography variant="caption">
            {formatDateTime(row.annulment.created_at)}
          </Typography>
        </Stack>
      ) : (
        <StatusChip label="Vigente" variant="success" />
      ),
  },
];

/** Consulta de movimientos inmutables del estudiante (RF-MOV-003). */
export function MovementHistoryWindow({
  onClose,
  studentId,
  enrolment,
  studentLabel,
  enrolmentLabel,
  onChanged,
}) {
  const [tab, setTab] = useState("history");
  const [movement, setMovement] = useState(null);
  const [busy, setBusy] = useState(false);
  const [sourceConsumed, setSourceConsumed] = useState(false);
  const [message, setMessage] = useState("");
  const loadMovements = useCallback(
    (params) =>
      enrolmentsService.listMovements({ ...params, student_id: studentId }),
    [studentId]
  );
  const list = usePaginatedList(loadMovements, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });
  const refresh = () => {
    list.refresh();
    onChanged?.();
  };
  const submit = async (kind, payload) => {
    if (kind === "annulment")
      await enrolmentsService.annulMovement(movement.public_id, payload);
    else if (kind === "withdrawal")
      await enrolmentsService.withdraw(enrolment.public_id, payload);
    else await enrolmentsService.changeSection(enrolment.public_id, payload);
    setSourceConsumed(true);
    setMessage(
      "Movimiento registrado. Para registrar otro cambio o retiro, vuelva a abrir la matrícula desde la lista actualizada."
    );
    setTab("history");
    setMovement(null);
    refresh();
  };

  return (
    <FloatingWindow
      busy={busy}
      description="La fecha de vigencia representa desde cuando surtio efecto el movimiento; la fecha de registro conserva cuando fue documentado en el sistema."
      footer={null}
      onClose={() => {
        if (!busy) onClose();
      }}
      open
      title="Historial de movimientos"
      width={WINDOW_WIDTH.large}
    >
      <Stack gap={2}>
        {studentLabel ? (
          <Typography component="div" variant="subtitle2">
            {studentLabel}
          </Typography>
        ) : null}
        {enrolmentLabel ? (
          <Typography component="div" color="text.secondary">
            {enrolmentLabel}
          </Typography>
        ) : null}
        {message ? <Alert severity="success">{message}</Alert> : null}
        <Tabs
          value={tab}
          onChange={(_event, next) => {
            setTab(next);
            if (next === "new") setMovement(null);
          }}
        >
          <Tab disabled={busy} value="history" label="Historial" />
          <Tab
            disabled={busy || !enrolment || sourceConsumed}
            value="new"
            label="Registrar movimiento"
          />
          {movement ? (
            <Tab disabled={busy} value="annul" label="Anular movimiento" />
          ) : null}
        </Tabs>
        {tab === "history" ? (
          <>
            {!enrolment ? (
              <Alert severity="info">
                Abra Movimientos desde una matrícula vigente para registrar
                cambios de sección o retiros.
              </Alert>
            ) : null}
            <ListSection
              columns={COLUMNS}
              emptyMessage="Este estudiante no tiene movimientos registrados."
              getRowKey={(movement) => movement.public_id}
              list={list}
              showInactiveToggle={false}
              subtitle="Historial institucional inmutable"
              title="Movimientos del estudiante"
              action={
                <Button onClick={list.refresh}>Actualizar historial</Button>
              }
              renderActions={(row) =>
                row.supports_annulment && !row.annulment ? (
                  <Button
                    onClick={() => {
                      setMovement(row);
                      setTab("annul");
                      setMessage("");
                    }}
                  >
                    Anular movimiento
                  </Button>
                ) : null
              }
            />
          </>
        ) : (
          <MovementForm
            key={movement?.public_id ?? "new"}
            enrolment={enrolment}
            movement={tab === "annul" ? movement : null}
            onSubmit={submit}
            onBusyChange={setBusy}
            onFailure={refresh}
            onCancel={() => setTab("history")}
          />
        )}
      </Stack>
    </FloatingWindow>
  );
}
