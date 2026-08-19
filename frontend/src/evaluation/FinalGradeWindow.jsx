import { useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { evaluationService } from "@evaluation/evaluationService.js";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

/**
 * Consulta de resultado: nota final de un estudiante en una subarea (RF-RES-001).
 *
 * La nota final es el promedio de las notas de unidad ya registradas; se
 * recalcula ante cualquier corrección mientras el ciclo esté abierto. Una
 * unidad sin nota es "sin calificar", no cero: se distingue con su propia
 * etiqueta y con el conteo de unidades pendientes, igual que el promedio en
 * curso (RF-CAL-003), del que esta consulta reutiliza el mismo cálculo.
 */
export function FinalGradeWindow({ cycleId, onClose }) {
  const [enrolmentId, setEnrolmentId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const canQuery = enrolmentId !== "" && subjectId !== "";

  const handleQuery = async (event) => {
    event.preventDefault();
    if (!canQuery) return;

    setLoading(true);
    setError("");
    setData(null);
    try {
      const result = await evaluationService.getFinalSubjectGrade(
        cycleId,
        enrolmentId,
        subjectId
      );
      setData(result);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <FloatingWindow
      description="Nota final de la subárea: promedio de las notas de unidad registradas hasta ahora."
      footer={
        <Button onClick={onClose} variant="text">
          Cerrar
        </Button>
      }
      onClose={onClose}
      open
      title="Consultar resultado"
      width={WINDOW_WIDTH.compact}
    >
      <Stack component="form" gap={2} onSubmit={handleQuery}>
        <TextField
          label="ID de inscripcion"
          onChange={(event) => setEnrolmentId(event.target.value)}
          size="small"
          type="number"
          value={enrolmentId}
        />
        <TextField
          label="ID de subarea"
          onChange={(event) => setSubjectId(event.target.value)}
          size="small"
          type="number"
          value={subjectId}
        />
        <Button
          disabled={!canQuery || loading}
          type="submit"
          variant="contained"
        >
          Consultar
        </Button>

        {loading ? <CircularProgress size={24} /> : null}
        {error ? <Alert severity="error">{error}</Alert> : null}
        {!loading && !error && data ? (
          <Stack gap={0.5}>
            <Typography variant="h4">
              {data.average != null ? data.average : "Sin calificar"}
            </Typography>
            <Typography color="text.secondary" variant="body2">
              {data.graded_units} de {data.total_units} unidades calificadas
              {data.pending_units > 0
                ? ` — ${data.pending_units} pendiente${data.pending_units === 1 ? "" : "s"} de registrar`
                : ""}
            </Typography>
          </Stack>
        ) : null}
      </Stack>
    </FloatingWindow>
  );
}
