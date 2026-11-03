import { lazy, Suspense, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import QrCodeScannerOutlinedIcon from "@mui/icons-material/QrCodeScannerOutlined";

import {
  attendanceService,
  MOVEMENT_LABEL,
  MOVEMENT_VARIANT,
  SCAN_REJECTION_MESSAGE,
} from "@attendance/attendanceService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { formatDateTime } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";

import { StudentCell } from "./StudentCell.jsx";
import { formatRemaining } from "./studentSearch.js";

const ScanCaptureWindow = lazy(() =>
  import("./ScanCaptureWindow.jsx").then((module) => ({
    default: module.ScanCaptureWindow,
  }))
);

const EVENT_COLUMNS = [
  {
    key: "student",
    label: "Estudiante",
    render: (row) => <StudentCell student={row.student} />,
  },
  {
    key: "movement_type",
    label: "Movimiento",
    render: (row) => (
      <StatusChip
        label={MOVEMENT_LABEL[row.movement_type] ?? row.movement_type}
        variant={MOVEMENT_VARIANT[row.movement_type] ?? "neutral"}
      />
    ),
  },
  {
    key: "captured_at",
    label: "Capturado",
    render: (row) => formatDateTime(row.captured_at),
  },
];

/** Milisegundos hasta `expiresAt`, actualizados cada segundo. */
function useRemaining(expiresAt) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!expiresAt) return undefined;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [expiresAt]);
  return expiresAt ? new Date(expiresAt).getTime() - now : null;
}

/**
 * Turno de captura del operador (AS1; RF-ASI-009, RF-AUT-005): abrir, ver su
 * vencimiento y lo ya capturado en él, y confirmarlo. Los movimientos se
 * guardan al escanearlos; confirmar solo cierra el turno. Un turno vencido lo
 * cierra el backend y el escaneo siguiente se rechaza con
 * `capture_batch_expired`.
 */
export function CaptureShiftCard() {
  const current = useQuery({
    queryKey: queryKeys.attendance("capture-batch", "current"),
    queryFn: () => attendanceService.currentCaptureBatch(),
  });
  const batch = current.data?.capture_batch ?? null;
  const events = current.data?.events ?? [];
  const remaining = useRemaining(batch?.expires_at);
  const expired = remaining !== null && remaining <= 0;

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [expiredNotice, setExpiredNotice] = useState(false);

  const run = async (action) => {
    setBusy(true);
    setError("");
    try {
      await action();
      await current.refetch();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const openShift = () =>
    run(async () => {
      await attendanceService.openCaptureBatch();
      setExpiredNotice(false);
    });

  const confirmShift = () =>
    run(async () => {
      setConfirming(false);
      await attendanceService.confirmCaptureBatch(batch.public_id);
    });

  return (
    <SectionCard
      action={
        <Stack direction="row" flexWrap="wrap" gap={1}>
          {batch && !expired ? (
            <Button
              disabled={busy}
              onClick={() => setConfirming(true)}
              variant="outlined"
            >
              Confirmar turno
            </Button>
          ) : (
            <Button
              disabled={busy || current.isPending}
              onClick={openShift}
              variant="outlined"
            >
              Abrir turno
            </Button>
          )}
          <Button
            onClick={() => setScanning(true)}
            startIcon={<QrCodeScannerOutlinedIcon fontSize="small" />}
            variant="contained"
          >
            Registrar por escaneo
          </Button>
        </Stack>
      }
      subtitle="Lo escaneado en el turno se recupera aunque se pierda la sesión."
      title="Turno de captura"
    >
      <Stack gap={1.5} sx={{ px: { xs: 2, md: 3 }, py: 2 }}>
        {current.error ? (
          <Alert severity="error">{current.error.message}</Alert>
        ) : null}
        {error ? (
          <Alert role="alert" severity="error">
            {error}
          </Alert>
        ) : null}
        {expiredNotice || (batch && expired) ? (
          <Alert severity="warning">
            {SCAN_REJECTION_MESSAGE.capture_batch_expired}
          </Alert>
        ) : null}
        {current.isPending ? (
          <Typography role="status">Cargando turno…</Typography>
        ) : batch ? (
          <Stack
            alignItems={{ sm: "center" }}
            direction={{ xs: "column", sm: "row" }}
            gap={1.5}
          >
            <StatusChip
              label={expired ? "Vencido" : "Abierto"}
              variant={expired ? "danger" : "success"}
            />
            <Typography variant="body2">
              {batch.expires_at
                ? `Vence el ${formatDateTime(batch.expires_at)}`
                : "Sin vencimiento configurado"}
            </Typography>
            {batch.expires_at && !expired ? (
              <Typography aria-live="polite" fontWeight={700} variant="body2">
                Quedan {formatRemaining(remaining)}
              </Typography>
            ) : null}
            <Typography color="text.secondary" variant="body2">
              {events.length === 1
                ? "1 movimiento capturado"
                : `${events.length} movimientos capturados`}
            </Typography>
          </Stack>
        ) : (
          <Typography color="text.secondary" variant="body2">
            No hay un turno de captura abierto. Abra uno para que lo escaneado
            quede agrupado y se pueda recuperar; también puede escanear sin
            turno.
          </Typography>
        )}
      </Stack>
      {batch && events.length > 0 ? (
        <SectionTableArea>
          <DataTable
            columns={EVENT_COLUMNS}
            getRowKey={(row) => row.public_id}
            rows={events}
          />
        </SectionTableArea>
      ) : null}
      <Box>
        <ConfirmDialog
          busy={busy}
          confirmText="Confirmar turno"
          message={`Se cierra el turno con ${events.length} movimientos. Ya estaban guardados; confirmar solo deja de ofrecerlo para recuperar.`}
          onClose={() => setConfirming(false)}
          onConfirm={confirmShift}
          open={confirming}
          title="Confirmar turno de captura"
        />
      </Box>
      <Suspense fallback={null}>
        {scanning ? (
          <ScanCaptureWindow
            captureBatchId={batch && !expired ? batch.public_id : ""}
            onClose={() => setScanning(false)}
            onRecorded={(result) => {
              if (result?.reason_code === "capture_batch_expired") {
                setExpiredNotice(true);
              }
              current.refetch();
            }}
          />
        ) : null}
      </Suspense>
    </SectionCard>
  );
}
