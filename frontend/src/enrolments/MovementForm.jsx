import { useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { academicsService } from "@academics/academicsService.js";
import { collectAllPages } from "@shared/api/pages.js";
import { useDependentCatalogOptions } from "@shared/catalogs/useCatalogOptions.js";
import { DateField } from "@ui/forms/DateField.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { formatDate } from "@shared/utils/format.js";

async function loadMovementSections(dependency) {
  const [cycleId, gradeId] = dependency.split("|");
  const rows = await collectAllPages((params) =>
    academicsService.listSections({
      ...params,
      academic_cycle_id: cycleId,
      grade_id: gradeId,
    })
  );
  return rows.map((row) => ({
    value: row.public_id,
    label: [row.grade?.name, row.name, row.shift?.name]
      .filter(Boolean)
      .join(" · "),
  }));
}

const KINDS = [
  { value: "section_change", label: "Cambio de sección" },
  { value: "withdrawal", label: "Retiro" },
];

/** Inline capture and review. Eligibility and side effects belong to the API. */
export function MovementForm({
  enrolment,
  movement,
  onSubmit,
  onCancel,
  onBusyChange,
  onFailure,
}) {
  const [kind, setKind] = useState(movement ? "annulment" : "section_change");
  const [sectionId, setSectionId] = useState("");
  const [effectiveOn, setEffectiveOn] = useState("");
  const [reason, setReason] = useState("");
  const [review, setReview] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const sections = useDependentCatalogOptions(
    loadMovementSections,
    kind === "section_change"
      ? `${enrolment.academic_cycle_id}|${enrolment.grade_id}`
      : ""
  );
  const options = sections.options.filter(
    (row) => row.value !== enrolment?.section_id
  );
  const change = (setter) => (event) => {
    setter(event.target.value);
    setReview(null);
    setError("");
  };
  const handleReview = (event) => {
    event.preventDefault();
    if (busy) return;
    setError("");
    if (kind !== "annulment" && !effectiveOn) {
      setError("Indique la fecha de vigencia.");
      return;
    }
    if (kind === "section_change" && !sectionId) {
      setError("Seleccione la sección de destino.");
      return;
    }
    if (kind !== "section_change" && !reason.trim()) {
      setError("Escriba el motivo.");
      return;
    }
    const payload =
      kind === "section_change"
        ? { new_section_id: sectionId, effective_on: effectiveOn }
        : kind === "withdrawal"
          ? { reason: reason.trim(), effective_on: effectiveOn }
          : { reason: reason.trim() };
    setReview({
      kind,
      payload,
      sectionLabel: options.find((row) => row.value === sectionId)?.label,
    });
  };
  const confirm = async () => {
    if (busy || !review) return;
    setBusy(true);
    onBusyChange(true);
    setError("");
    try {
      await onSubmit(review.kind, review.payload);
    } catch (submitError) {
      setError(submitError.message);
      setReview(null);
      onFailure?.();
    } finally {
      setBusy(false);
      onBusyChange(false);
    }
  };
  return (
    <Box component="form" noValidate onSubmit={handleReview}>
      <Stack gap={2}>
        {movement ? (
          <Alert severity="warning">
            La anulación agrega una corrección y conserva el movimiento
            original. Su aplicación depende del estado actual de las matrículas
            y del ciclo.
          </Alert>
        ) : (
          <FormSelect
            label="Tipo de movimiento"
            disabled={busy}
            options={KINDS}
            value={kind}
            onChange={change(setKind)}
          />
        )}
        {kind === "section_change" ? (
          <FormSelect
            label="Sección de destino"
            placeholder="Seleccione una sección"
            options={options}
            loading={sections.loading}
            error={sections.error}
            disabled={busy}
            value={sectionId}
            onChange={change(setSectionId)}
            helperText="Secciones del mismo ciclo y grado. El cupo se valida al confirmar."
          />
        ) : null}
        {kind !== "annulment" ? (
          <DateField
            label="Vigente desde"
            disabled={busy}
            value={effectiveOn}
            onChange={change(setEffectiveOn)}
          />
        ) : null}
        {kind !== "section_change" ? (
          <FormTextField
            label={
              kind === "annulment" ? "Motivo de anulación" : "Causa del retiro"
            }
            required
            multiline
            minRows={2}
            disabled={busy}
            value={reason}
            onChange={change(setReason)}
          />
        ) : null}
        {kind === "withdrawal" ? (
          <Alert severity="warning">
            El retiro cierra la matrícula y afecta el acceso y la credencial del
            estudiante. El historial se conserva.
          </Alert>
        ) : null}
        {error ? <Alert severity="error">{error}</Alert> : null}
        {review ? (
          <Stack gap={1}>
            <Typography variant="subtitle2">
              Revise antes de confirmar
            </Typography>
            <Typography>
              {review.kind === "annulment"
                ? "Anulación del movimiento seleccionado"
                : review.kind === "withdrawal"
                  ? "Retiro del estudiante"
                  : `Cambio a ${review.sectionLabel}`}
            </Typography>
            {review.payload.effective_on ? (
              <Typography>
                Vigencia: {formatDate(review.payload.effective_on)}
              </Typography>
            ) : null}
            {review.payload.reason ? (
              <Typography sx={{ whiteSpace: "pre-wrap" }}>
                Motivo: {review.payload.reason}
              </Typography>
            ) : null}
            <Stack direction="row" gap={1}>
              <Button disabled={busy} onClick={() => setReview(null)}>
                Volver a editar
              </Button>
              <Button
                disabled={busy}
                variant="contained"
                color={kind === "withdrawal" ? "error" : "primary"}
                onClick={confirm}
              >
                {busy
                  ? "Procesando…"
                  : kind === "annulment"
                    ? "Confirmar anulación"
                    : kind === "withdrawal"
                      ? "Confirmar retiro"
                      : "Confirmar cambio de sección"}
              </Button>
            </Stack>
          </Stack>
        ) : (
          <Button disabled={busy} type="submit" variant="contained">
            Revisar movimiento
          </Button>
        )}
        <Button disabled={busy} onClick={onCancel}>
          Volver al historial
        </Button>
      </Stack>
    </Box>
  );
}
