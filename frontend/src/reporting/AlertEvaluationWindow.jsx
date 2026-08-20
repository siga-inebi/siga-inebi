import { useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";

import { reportingService } from "@reporting/reportingService.js";
import { useShiftCatalog } from "@shared/catalogs/academicCatalogs.js";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { DetailField } from "@ui/layout/DetailWindow.jsx";

/**
 * Recalculo de alertas de una jornada y fecha.
 *
 * Es una accion, no un formulario de alta: no crea nada nuevo por si misma, le
 * pide al backend volver a evaluar los datos de asistencia de ese dia. El
 * resultado se muestra desglosado porque saber CUANTAS alertas se sincronizaron,
 * cuantas quedaron superadas y cuantas son por frecuencia es justamente lo que
 * dice si el recalculo hizo algo.
 */
export function AlertEvaluationWindow({ onClose, onEvaluated }) {
  const shifts = useShiftCatalog();

  const [shiftId, setShiftId] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = shiftId !== "" && eventDate !== "" && !submitting;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError("");
    setResult(null);
    try {
      const data = await reportingService.evaluate({
        shift_id: shiftId.trim(),
        event_date: eventDate,
      });
      setResult(data);
      onEvaluated?.();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <FloatingWindow
      description="Vuelve a evaluar la asistencia de una jornada y sincroniza sus alertas."
      footer={
        <>
          <Button disabled={submitting} onClick={onClose} variant="text">
            Cerrar
          </Button>
          <Button
            disabled={!canSubmit}
            form="alert-evaluation-form"
            startIcon={submitting ? <CircularProgress size={16} /> : undefined}
            type="submit"
            variant="contained"
          >
            {submitting ? "Evaluando…" : "Recalcular"}
          </Button>
        </>
      }
      onClose={onClose}
      open
      title="Recalcular alertas de la jornada"
    >
      <Box component="form" id="alert-evaluation-form" onSubmit={handleSubmit}>
        <Stack gap={2}>
          <FormSelect
            disabled={submitting}
            error={shifts.error}
            fullWidth
            helperText={
              !shifts.loading && shifts.options.length === 0
                ? "No hay jornadas registradas."
                : undefined
            }
            label="Jornada"
            loading={shifts.loading}
            onChange={(event) => setShiftId(event.target.value)}
            options={shifts.options}
            placeholder="Seleccione una jornada"
            value={shiftId}
          />
          <FormTextField
            disabled={submitting}
            label="Fecha de la jornada"
            onChange={(event) => setEventDate(event.target.value)}
            slotProps={{ inputLabel: { shrink: true } }}
            type="date"
            value={eventDate}
          />

          {error ? <Alert severity="error">{error}</Alert> : null}

          {result ? (
            <>
              <Alert severity="success">Recalculo completado.</Alert>
              <Box
                component="dl"
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                  gap: 2,
                  m: 0,
                }}
              >
                <DetailField
                  label="Alertas sincronizadas"
                  value={result.synced_alerts?.length ?? 0}
                />
                <DetailField
                  label="Alertas superadas"
                  value={result.superseded_source_alerts?.length ?? 0}
                />
                <DetailField
                  label="Ausencias detectadas"
                  value={result.absence_alerts?.length ?? 0}
                />
                <DetailField
                  label="Por frecuencia de ausencias"
                  value={result.frequent_absence_alerts?.length ?? 0}
                />
              </Box>
            </>
          ) : null}
        </Stack>
      </Box>
    </FloatingWindow>
  );
}
