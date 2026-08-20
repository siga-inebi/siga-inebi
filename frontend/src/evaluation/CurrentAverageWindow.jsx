import { useEffect, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { evaluationService } from "@evaluation/evaluationService.js";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

/**
 * Promedio en curso de un estudiante en una subarea (RF-CAL-003).
 *
 * Una unidad sin nota es "sin calificar", no cero: nunca se muestra como 0,
 * ni se incluye en el promedio. Se distingue con su propia etiqueta y con el
 * conteo de unidades pendientes, para que no se confunda con una nota real.
 */
export function CurrentAverageWindow({
  cycleId,
  enrolmentId,
  onClose,
  subjectId,
}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    evaluationService
      .getCurrentAverage(cycleId, enrolmentId, subjectId)
      .then((result) => {
        if (active) setData(result);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [cycleId, enrolmentId, subjectId]);

  return (
    <FloatingWindow
      footer={
        <Button onClick={onClose} variant="text">
          Cerrar
        </Button>
      }
      onClose={onClose}
      open
      title="Promedio en curso"
      width={WINDOW_WIDTH.compact}
    >
      <Stack gap={1.5}>
        {loading ? <CircularProgress size={24} /> : null}
        {error ? <Alert severity="error">{error}</Alert> : null}
        {!loading && !error && data ? (
          <>
            <Typography variant="h4">
              {data.average != null ? data.average : "Sin calificar"}
            </Typography>
            <Typography color="text.secondary" variant="body2">
              {data.graded_units} de {data.total_units} unidades calificadas
              {data.pending_units > 0
                ? ` — ${data.pending_units} pendiente${data.pending_units === 1 ? "" : "s"} de registrar`
                : ""}
            </Typography>
          </>
        ) : null}
      </Stack>
    </FloatingWindow>
  );
}
