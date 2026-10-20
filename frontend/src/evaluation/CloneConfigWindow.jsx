import { useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";

import { evaluationService } from "@evaluation/evaluationService.js";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

/**
 * Clonar la configuración de evaluación a otro ciclo (RF-EVC-006, V6).
 *
 * Solo ofrece ciclos en borrador: el backend exige un destino en preparación y
 * sin unidades propias, y traslada cada fecha por la diferencia entre los
 * inicios de ambos ciclos. Si el destino ya tiene unidades, el motivo del
 * rechazo se muestra aquí sin cerrar la ventana.
 */
export function CloneConfigWindow({ cycle, cycles, onClose }) {
  const targets = cycles.filter(
    (item) => item.status === "draft" && item.public_id !== cycle.public_id
  );
  const [target, setTarget] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(null);

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      await evaluationService.cloneConfig(cycle.public_id, target);
      setDone(targets.find((item) => item.public_id === target));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <FloatingWindow
      busy={busy}
      description={`Copia las unidades de «${cycle.name}», con sus ventanas de captura y recuperación, y su número de unidades. Las fechas se trasladan según el inicio del ciclo destino.`}
      footer={
        done ? (
          <Button onClick={onClose} variant="contained">
            Cerrar
          </Button>
        ) : (
          <>
            <Button disabled={busy} onClick={onClose} variant="text">
              Cancelar
            </Button>
            <Button
              disabled={busy || !target}
              onClick={submit}
              startIcon={busy ? <CircularProgress size={16} /> : undefined}
              variant="contained"
            >
              {busy ? "Clonando…" : "Clonar configuración"}
            </Button>
          </>
        )
      }
      onClose={onClose}
      open
      title="Clonar configuración a otro ciclo"
      width={WINDOW_WIDTH.compact}
    >
      <Stack gap={2}>
        {done ? (
          <Alert severity="success">
            La configuración se copió a «{done.name}». Revise sus unidades
            eligiendo ese ciclo.
          </Alert>
        ) : (
          <>
            <FormSelect
              fullWidth
              helperText={
                targets.length === 0
                  ? "No hay ciclos en borrador. Cree o devuelva a borrador el ciclo destino antes de clonar."
                  : "Solo ciclos en borrador y sin unidades propias."
              }
              label="Ciclo destino"
              onChange={(event) => setTarget(event.target.value)}
              options={targets.map((item) => ({
                value: item.public_id,
                label: item.name,
              }))}
              placeholder="Seleccione un ciclo"
              value={target}
            />
            {error ? (
              <Alert role="alert" severity="error">
                {error}
              </Alert>
            ) : null}
          </>
        )}
      </Stack>
    </FloatingWindow>
  );
}
