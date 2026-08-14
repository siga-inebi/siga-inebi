import { useId, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";

import { BaseDrawer } from "@ui/layout/BaseDrawer.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";

/**
 * Formulario de alta y edicion de catalogo, en panel lateral.
 *
 * Conserva el contrato declarativo de campos que ya usaban las pantallas
 * (`{ name, label, type, help, required, options, min, placeholder }`), asi que
 * migrar una pantalla a MUI no obliga a reescribir su definicion de formulario.
 *
 * `onSubmit` recibe los valores ya normalizados y puede rechazar: el mensaje del
 * backend se muestra SIN cerrar el panel, para no perder lo escrito. Cerrar en
 * el error es como se pierde media hora de captura.
 */
export function CatalogueFormDrawer({
  description,
  fields,
  initialValues,
  onCancel,
  onSubmit,
  open,
  submitLabel = "Guardar",
  title,
}) {
  const [values, setValues] = useState(initialValues);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Dos formularios pueden convivir en la pantalla (nivel y grado, por
  // ejemplo); el prefijo evita que compartan el id de un campo homonimo.
  const formId = useId();

  const setValue = (name, value) =>
    setValues((current) => ({ ...current, [name]: value }));

  const handleSubmit = async (event) => {
    event.preventDefault();

    const missing = fields.find(
      (field) =>
        field.required &&
        (field.type === "number"
          ? values[field.name] === "" || values[field.name] === null
          : !String(values[field.name] ?? "").trim())
    );

    if (missing) {
      setError(`Complete el campo ${missing.label.toLowerCase()}.`);
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      await onSubmit(normalize(fields, values));
    } catch (submitError) {
      setError(submitError.message);
      setSubmitting(false);
    }
  };

  return (
    <BaseDrawer
      busy={submitting}
      description={description}
      footer={
        <>
          <Button disabled={submitting} onClick={onCancel} variant="text">
            Cancelar
          </Button>
          <Button
            disabled={submitting}
            form={formId}
            startIcon={submitting ? <CircularProgress size={16} /> : undefined}
            type="submit"
            variant="contained"
          >
            {submitting ? "Guardando…" : submitLabel}
          </Button>
        </>
      }
      onClose={onCancel}
      open={open}
      title={title}
    >
      {/* El submit vive en el pie del panel, fuera del <form>: se enlazan por
          el atributo form/id, que es el mecanismo estandar para eso. */}
      <Stack component="form" gap={2} id={formId} noValidate onSubmit={handleSubmit}>
        {error ? (
          <Alert role="alert" severity="error" variant="outlined">
            {error}
          </Alert>
        ) : null}

        {fields.map((field) => (
          <CatalogueField
            disabled={submitting}
            field={field}
            key={field.name}
            onChange={setValue}
            value={values[field.name]}
          />
        ))}
      </Stack>
    </BaseDrawer>
  );
}

function CatalogueField({ disabled, field, onChange, value }) {
  if (field.type === "checkbox") {
    return (
      <FormControlLabel
        control={
          <Switch
            checked={Boolean(value)}
            disabled={disabled}
            name={field.name}
            onChange={(event) => onChange(field.name, event.target.checked)}
          />
        }
        label={field.label}
      />
    );
  }

  if (field.type === "select") {
    return (
      <FormSelect
        disabled={disabled}
        fullWidth
        helperText={field.help}
        label={field.label}
        name={field.name}
        onChange={(event) => onChange(field.name, event.target.value)}
        options={field.options}
        placeholder="Seleccione una opcion"
        required={field.required}
        value={value ?? ""}
      />
    );
  }

  return (
    <FormTextField
      disabled={disabled}
      helperText={field.help}
      label={field.label}
      name={field.name}
      onChange={(event) => onChange(field.name, event.target.value)}
      placeholder={field.placeholder}
      required={field.required}
      slotProps={
        field.type === "number" && field.min != null
          ? { htmlInput: { min: field.min } }
          : undefined
      }
      type={field.type === "number" ? "number" : "text"}
      value={value ?? ""}
    />
  );
}

/**
 * Los inputs siempre devuelven texto; el backend espera enteros y booleanos.
 * Los campos de texto se recortan para que un espacio no pase como nombre.
 */
function normalize(fields, values) {
  const payload = {};

  for (const field of fields) {
    const value = values[field.name];

    if (field.type === "checkbox") {
      payload[field.name] = Boolean(value);
    } else if (field.type === "number") {
      payload[field.name] = Number(value);
    } else {
      payload[field.name] = String(value ?? "").trim();
    }
  }

  return payload;
}
