import { useCallback, useEffect, useId, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";

import {
  documentsService,
  templateKindOptions,
} from "@documents/documentsService.js";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";

/** Captures consent for a particular UUID; refreshing availability never grants fresh consent. */
export function TemplateFormWindow({ template, kinds, onCancel, onSubmit }) {
  const [values, setValues] = useState({
    name: template?.name ?? "",
    code: template?.code ?? "",
    kind: template?.kind ?? kinds[0]?.code ?? "",
    issuance_use: template?.issuance_use ?? "none",
    description: template?.description ?? "",
    content: template?.content ?? "",
  });
  const [uses, setUses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [availabilityError, setAvailabilityError] = useState("");
  const [confirmedId, setConfirmedId] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const formId = useId();

  const loadUses = useCallback(async () => {
    setLoading(true);
    setAvailabilityError("");
    try {
      setUses(await documentsService.listTemplateIssuanceUses());
    } catch (requestError) {
      setAvailabilityError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    loadUses();
  }, [loadUses]);

  const occupant =
    template?.is_active === false
      ? null
      : uses.find((use) => use.code === values.issuance_use)?.active_template;
  const replacing =
    occupant && occupant.public_id !== template?.public_id ? occupant : null;
  const setValue = (name, value) => {
    setValues((current) => ({ ...current, [name]: value }));
    if (name === "issuance_use") setConfirmedId("");
  };
  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    if (
      !values.name.trim() ||
      !values.kind ||
      (!template && !values.code.trim())
    ) {
      setError("Complete nombre, código y tipo de la plantilla.");
      return;
    }
    if (replacing && confirmedId !== replacing.public_id) {
      setError("Confirme el reemplazo de la plantilla activa indicada.");
      return;
    }
    setSubmitting(true);
    const { code, ...editable } = values;
    const payload = template ? editable : { ...editable, code };
    if (replacing) payload.replaces_template_id = confirmedId;
    try {
      await onSubmit(payload);
    } catch (requestError) {
      setError(requestError.message);
      await loadUses();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <FloatingWindow
      busy={submitting}
      description={
        template
          ? `Guardar genera una version nueva de la plantilla. El codigo ${template.code} es inmutable.`
          : "El código identifica la plantilla y no se puede cambiar después del alta."
      }
      footer={
        <>
          <Button disabled={submitting} onClick={onCancel}>
            Cancelar
          </Button>
          <Button
            disabled={submitting || loading || Boolean(availabilityError)}
            form={formId}
            type="submit"
            variant="contained"
          >
            {submitting
              ? "Guardando…"
              : template
                ? "Guardar version"
                : "Crear plantilla"}
          </Button>
        </>
      }
      onClose={onCancel}
      open
      title={
        template ? `Editar ${template.name}` : "Nueva plantilla documental"
      }
    >
      <Stack
        component="form"
        id={formId}
        gap={2}
        noValidate
        onSubmit={handleSubmit}
      >
        {error ? <Alert severity="error">{error}</Alert> : null}
        {availabilityError ? (
          <Alert
            severity="error"
            action={<Button onClick={loadUses}>Reintentar</Button>}
          >
            {availabilityError}
          </Alert>
        ) : null}
        {template?.is_active === false ? (
          <Alert severity="info">
            Esta plantilla está desactivada. Guardar una versión no la activa.
          </Alert>
        ) : null}
        <FormTextField
          disabled={submitting}
          label="Nombre"
          required
          value={values.name}
          onChange={(event) => setValue("name", event.target.value)}
        />
        {!template ? (
          <FormTextField
            disabled={submitting}
            label="Codigo"
            required
            value={values.code}
            onChange={(event) => setValue("code", event.target.value)}
          />
        ) : null}
        <FormSelect
          disabled={submitting}
          label="Tipo"
          helperText="Clasificación del documento. El uso de emisión se elige por separado."
          required
          options={templateKindOptions(kinds)}
          value={values.kind}
          onChange={(event) => setValue("kind", event.target.value)}
        />
        <FormSelect
          disabled={submitting || loading || Boolean(availabilityError)}
          label="Se usa para"
          options={[
            { value: "none", label: "Ninguna" },
            ...uses.map((use) => ({
              value: use.code,
              label: `${use.label}${use.active_template && use.active_template.public_id !== template?.public_id ? ` · Activa: ${use.active_template.name}` : ""}`,
            })),
          ]}
          value={loading ? "none" : values.issuance_use}
          onChange={(event) => setValue("issuance_use", event.target.value)}
        />
        {replacing ? (
          <Box>
            <Alert severity="warning">
              Este uso ya tiene una plantilla activa. Al reemplazarla se
              conserva su historial.
            </Alert>
            <FormControlLabel
              label={`Reemplazar “${replacing.name}”`}
              control={
                <Checkbox
                  disabled={submitting}
                  checked={confirmedId === replacing.public_id}
                  onChange={(event) =>
                    setConfirmedId(
                      event.target.checked ? replacing.public_id : ""
                    )
                  }
                />
              }
            />
          </Box>
        ) : null}
        <FormTextField
          disabled={submitting}
          label="Descripcion (opcional)"
          value={values.description}
          onChange={(event) => setValue("description", event.target.value)}
        />
        <FormTextField
          disabled={submitting}
          label="Contenido de la plantilla"
          multiline
          minRows={8}
          helperText="Use únicamente etiquetas disponibles, por ejemplo {{student.full_name}}."
          value={values.content}
          onChange={(event) => setValue("content", event.target.value)}
        />
      </Stack>
    </FloatingWindow>
  );
}
