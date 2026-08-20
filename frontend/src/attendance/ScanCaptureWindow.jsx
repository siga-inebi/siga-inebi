import { useEffect, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";

import {
  attendanceService,
  MOVEMENT_LABEL,
  SCAN_OUTCOME_LABEL,
  SCAN_OUTCOME_VARIANT,
} from "@attendance/attendanceService.js";
import { formatDateTime } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

const MOVEMENT_OPTIONS = [
  { value: "entry", label: "Entrada" },
  { value: "exit", label: "Salida" },
];

/**
 * Registro de un movimiento por escaneo (RF-ASI-001/002/004/010).
 *
 * Como el carnet con QR real todavia no existe (RF-CRE-001), "escanear" es
 * escribir o inyectar el codigo del estudiante: el flujo queda listo para
 * conectar un lector de verdad sin rediseñarse.
 *
 * `clientEventId` se genera una sola vez por intento y se REUTILIZA si el
 * envio falla por red: eso es lo que hace que un reintento sea idempotente
 * (RF-ASI-010) en vez de crear un movimiento duplicado. Solo se genera un id
 * nuevo despues de un envio que sí completo (creado, duplicado informado o ya
 * procesado) — ahi empieza un intento distinto.
 */
export function ScanCaptureWindow({ onClose, onRecorded }) {
  const [studentCode, setStudentCode] = useState("");
  const [movementType, setMovementType] = useState("entry");
  const [shiftId, setShiftId] = useState("");
  const [controlPointId, setControlPointId] = useState("");
  const [clientEventId, setClientEventId] = useState(() => crypto.randomUUID());

  const [controlPoints, setControlPoints] = useState([]);
  const [controlPointsLoading, setControlPointsLoading] = useState(true);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  useEffect(() => {
    let active = true;
    attendanceService
      .listControlPoints({ page: 1 })
      .then((payload) => {
        if (active) setControlPoints(payload?.results || []);
      })
      .catch(() => {
        if (active) setControlPoints([]);
      })
      .finally(() => {
        if (active) setControlPointsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const canSubmit =
    studentCode.trim() !== "" &&
    shiftId.trim() !== "" &&
    controlPointId !== "" &&
    !submitting;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError("");
    try {
      const response = await attendanceService.recordScan({
        items: [
          {
            client_event_id: clientEventId,
            student_code: studentCode.trim(),
            shift_id: shiftId.trim(),
            control_point_id: controlPointId,
            movement_type: movementType,
            captured_at: new Date().toISOString(),
          },
        ],
      });
      setResult(response[0]);
      // El intento termino (con o sin exito de negocio): el proximo escaneo
      // es uno nuevo, con su propio id.
      setClientEventId(crypto.randomUUID());
      setStudentCode("");
      if (response[0].outcome === "created") onRecorded?.();
    } catch (requestError) {
      // Fallo de red o del servidor: NO se genera un id nuevo, para que
      // reintentar con el mismo boton reuse el mismo client_event_id.
      setError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <FloatingWindow
      description="Cada escaneo es idempotente: un reintento por fallo de red no duplica el movimiento."
      footer={
        <Button onClick={onClose} variant="text">
          Cerrar
        </Button>
      }
      onClose={onClose}
      open
      title="Registrar por escaneo"
      width={WINDOW_WIDTH.compact}
    >
      <Stack component="form" gap={2} onSubmit={handleSubmit}>
        <FormTextField
          helperText="Codigo leido del carnet del estudiante."
          label="Codigo de estudiante"
          onChange={(event) => setStudentCode(event.target.value)}
          required
          value={studentCode}
        />
        <FormSelect
          label="Movimiento"
          onChange={(event) => setMovementType(event.target.value)}
          options={MOVEMENT_OPTIONS}
          required
          value={movementType}
        />
        <FormSelect
          helperText={
            controlPoints.length === 0 && !controlPointsLoading
              ? "No hay puntos de control registrados todavia."
              : undefined
          }
          label="Punto de control"
          loading={controlPointsLoading}
          onChange={(event) => setControlPointId(event.target.value)}
          options={controlPoints.map((point) => ({
            value: point.public_id,
            label: `${point.name} (${point.code})`,
          }))}
          placeholder="Seleccione un punto de control"
          required
          value={controlPointId}
        />
        <FormTextField
          helperText="Provisional: mas adelante se resuelve por el punto de control."
          label="ID de jornada"
          onChange={(event) => setShiftId(event.target.value)}
          required
          value={shiftId}
        />

        <Button
          disabled={!canSubmit}
          startIcon={submitting ? <CircularProgress size={16} /> : undefined}
          type="submit"
          variant="contained"
        >
          {submitting ? "Registrando…" : "Registrar"}
        </Button>

        {error ? (
          <Alert role="alert" severity="error">
            {error}
          </Alert>
        ) : null}

        {result ? <ScanResult result={result} /> : null}
      </Stack>
    </FloatingWindow>
  );
}

function ScanResult({ result }) {
  const severity =
    result.outcome === "rejected"
      ? "error"
      : result.outcome === "duplicate_suppressed"
        ? "warning"
        : "success";

  return (
    <Alert severity={severity}>
      <Stack gap={0.5}>
        <StatusChip
          label={SCAN_OUTCOME_LABEL[result.outcome] ?? result.outcome}
          variant={SCAN_OUTCOME_VARIANT[result.outcome] ?? "neutral"}
        />
        {result.outcome === "duplicate_suppressed" && result.duplicate_of ? (
          <span>
            {MOVEMENT_LABEL[result.duplicate_of.movement_type] ??
              result.duplicate_of.movement_type}{" "}
            ya registrado a las{" "}
            {formatDateTime(result.duplicate_of.captured_at)}.
          </span>
        ) : null}
        {result.outcome === "rejected" && result.reason ? (
          <span>{result.reason}</span>
        ) : null}
      </Stack>
    </Alert>
  );
}
