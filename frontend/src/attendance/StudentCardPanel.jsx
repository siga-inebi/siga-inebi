import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import BadgeOutlinedIcon from "@mui/icons-material/BadgeOutlined";
import PrintOutlinedIcon from "@mui/icons-material/PrintOutlined";

import {
  attendanceService,
  CARD_STATUS_LABEL,
  CARD_STATUS_VARIANT,
} from "@attendance/attendanceService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { formatDateTime } from "@shared/utils/format.js";
import { printStudentCard } from "@shared/utils/print.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { ReasonDialog } from "@ui/feedback/ReasonDialog.jsx";
import { DetailField } from "@ui/layout/DetailWindow.jsx";

/**
 * Carné de un estudiante (AS2; RF-CRE-001..004): estado, emisión con el QR,
 * impresión y revocación.
 *
 * El QR solo viene en la respuesta de emisión y se muestra una vez: vive en
 * memoria mientras la pantalla está abierta, nunca en el dispositivo
 * (RNF-PRI-003). Reimprimir es revocar y emitir de nuevo; el carné anterior
 * queda como historia del expediente.
 *
 * @param {object} props
 * @param {string} props.studentId
 * @param {string} [props.studentName]
 */
export function StudentCardPanel({ studentId, studentName }) {
  const status = useQuery({
    queryKey: queryKeys.attendance("card-status", studentId),
    queryFn: () => attendanceService.cardStatus(studentId),
  });
  const [issued, setIssued] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [revoking, setRevoking] = useState(false);

  const current = status.data?.status ?? "none";

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

  const print = async () => {
    setBusy(true);
    setError("");
    try {
      const content = await attendanceService.cardPrintContent(studentId);
      if (!printStudentCard(content, issued.qr_code)) {
        setError(
          "El navegador bloqueó la ventana de impresión. Permita las ventanas emergentes de este sitio e intente de nuevo."
        );
      }
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Stack gap={2}>
      <Alert severity="info">
        El código QR solo se muestra al emitir el carné. Para reimprimirlo,
        revoque el carné vigente y emita uno nuevo; el anterior queda en el
        historial.
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

      {issued ? (
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
          <Box
            alt={`Código QR del carné de ${studentName ?? "el estudiante"}`}
            component="img"
            src={`data:image/png;base64,${issued.qr_code}`}
            sx={{ width: 160, height: 160, imageRendering: "pixelated" }}
          />
          <Stack gap={1}>
            <Typography fontWeight={700}>Carné emitido</Typography>
            <Typography color="text.secondary" variant="body2">
              Imprímalo ahora: al cerrar esta pantalla el QR ya no se puede
              volver a mostrar.
            </Typography>
            <Box>
              <Button
                disabled={busy}
                onClick={print}
                startIcon={<PrintOutlinedIcon fontSize="small" />}
                variant="contained"
              >
                Imprimir carné
              </Button>
            </Box>
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
