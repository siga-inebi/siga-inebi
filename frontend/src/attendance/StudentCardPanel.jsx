import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import BadgeOutlinedIcon from "@mui/icons-material/BadgeOutlined";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";

import {
  attendanceService,
  CARD_STATUS_LABEL,
  CARD_STATUS_VARIANT,
} from "@attendance/attendanceService.js";
import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { downloadResponseFile } from "@shared/utils/download.js";
import { formatDateTime } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { ReasonDialog } from "@ui/feedback/ReasonDialog.jsx";
import { DetailField } from "@ui/layout/DetailWindow.jsx";

/**
 * Carné de un estudiante (AS2; RF-CRE-001..004): estado, emisión, QR,
 * descarga y revocación.
 *
 * Con `attendance.credential.print` el QR del carné vigente se vuelve a pedir
 * cada vez que se abre la pantalla (el backend audita cada lectura) y el carné
 * se descarga en PNG o PDF. El QR vive solo en memoria mientras la pantalla
 * está abierta, nunca en el dispositivo (RNF-PRI-003). Revocar lo invalida; el
 * carné anterior queda como historia del expediente.
 *
 * @param {object} props
 * @param {string} props.studentId
 * @param {string} [props.studentName]
 */
export function StudentCardPanel({ studentId, studentName }) {
  const canPrint = usePermissions().can(PERMISSION.ATTENDANCE_CREDENTIAL_PRINT);
  const status = useQuery({
    queryKey: queryKeys.attendance("card-status", studentId),
    queryFn: () => attendanceService.cardStatus(studentId),
  });
  const [issued, setIssued] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [revoking, setRevoking] = useState(false);

  const current = status.data?.status ?? "none";
  // Recién emitido, el QR ya viene en la respuesta: no hace falta pedirlo.
  const qr = useQuery({
    queryKey: queryKeys.credentialQr(studentId, status.data?.public_id),
    queryFn: () => attendanceService.revealCardQr(studentId),
    enabled: canPrint && current === "active" && !issued,
    gcTime: 0,
    staleTime: Infinity,
    retry: false,
  });
  // Un carné revocado conserva su id: sin la condición seguiría mostrando el
  // QR que ya quedó en la cache de esta pantalla.
  const qrCode =
    issued?.qr_code ?? (current === "active" ? qr.data?.qr_code : null) ?? null;
  const canDownload = canPrint && (current === "active" || Boolean(issued));

  const issue = async () => {
    setBusy(true);
    setError("");
    try {
      setIssued(await attendanceService.issueCard(studentId));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  const download = async (format) => {
    setBusy(true);
    setError("");
    try {
      const file = await attendanceService.exportCards([studentId], format);
      downloadResponseFile(file, `carne-${studentId}.${format}`);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack gap={2}>
      <Alert severity="info">
        {canPrint
          ? "Mientras el carné esté vigente, su código QR se puede volver a ver y descargar; cada consulta queda registrada. Revocarlo lo invalida y el anterior queda en el historial."
          : "Para ver el código QR o descargar el carné vigente se necesita el permiso de impresión de carnés."}
      </Alert>
      {status.error ? (
        <Alert severity="error">{status.error.message}</Alert>
      ) : null}
      {status.isPending ? (
        <Typography role="status">Consultando carné…</Typography>
      ) : (
        <Box
          component="dl"
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" },
            gap: 2,
            m: 0,
          }}
        >
          <DetailField
            label="Estado"
            value={
              <StatusChip
                label={CARD_STATUS_LABEL[current] ?? current}
                variant={CARD_STATUS_VARIANT[current] ?? "neutral"}
              />
            }
          />
          <DetailField
            label="Emitido"
            value={
              status.data?.issued_at
                ? formatDateTime(status.data.issued_at)
                : null
            }
          />
          {current === "revoked" ? (
            <DetailField
              label="Revocación"
              value={[
                formatDateTime(status.data.revoked_at),
                status.data.revocation_reason,
              ]
                .filter(Boolean)
                .join(" · ")}
            />
          ) : null}
        </Box>
      )}

      {error ? (
        <Alert role="alert" severity="error">
          {error}
        </Alert>
      ) : null}

      {qr.error ? <Alert severity="error">{qr.error.message}</Alert> : null}

      {qrCode || canDownload ? (
        <Stack
          alignItems={{ sm: "center" }}
          direction={{ xs: "column", sm: "row" }}
          gap={2}
          sx={{
            p: 2,
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 2,
          }}
        >
          {qrCode ? (
            <Box
              alt={`Código QR del carné de ${studentName ?? "el estudiante"}`}
              component="img"
              src={`data:image/png;base64,${qrCode}`}
              sx={{ width: 160, height: 160, imageRendering: "pixelated" }}
            />
          ) : qr.isFetching ? (
            <Typography role="status">Cargando código QR…</Typography>
          ) : null}
          <Stack gap={1}>
            <Typography fontWeight={700}>
              {issued ? "Carné emitido" : "Carné vigente"}
            </Typography>
            {canDownload ? (
              <Stack direction="row" flexWrap="wrap" gap={1}>
                <Button
                  disabled={busy}
                  onClick={() => download("png")}
                  startIcon={<FileDownloadOutlinedIcon fontSize="small" />}
                  variant="contained"
                >
                  Descargar PNG
                </Button>
                <Button
                  disabled={busy}
                  onClick={() => download("pdf")}
                  startIcon={<FileDownloadOutlinedIcon fontSize="small" />}
                  variant="outlined"
                >
                  Descargar PDF
                </Button>
              </Stack>
            ) : null}
          </Stack>
        </Stack>
      ) : null}

      {!status.isPending ? (
        <Stack direction="row" flexWrap="wrap" gap={1}>
          {current !== "active" ? (
            <Button
              disabled={busy}
              onClick={issue}
              startIcon={<BadgeOutlinedIcon fontSize="small" />}
              variant="contained"
            >
              {current === "revoked" ? "Emitir carné nuevo" : "Emitir carné"}
            </Button>
          ) : (
            <Button
              color="error"
              disabled={busy}
              onClick={() => setRevoking(true)}
              variant="outlined"
            >
              Revocar carné
            </Button>
          )}
        </Stack>
      ) : null}

      <ReasonDialog
        confirmColor="error"
        confirmText="Revocar carné"
        message="El carné deja de servir para registrar movimientos de inmediato. No se borra: queda en el historial."
        onClose={() => setRevoking(false)}
        onConfirm={async (reason) => {
          await attendanceService.revokeCard(studentId, reason);
          setRevoking(false);
          setIssued(null);
        }}
        open={revoking}
        title="Revocar carné"
      />
    </Stack>
  );
}
