import { useEffect, useId, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";
import UploadFileIcon from "@mui/icons-material/UploadFileOutlined";

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
export function EntityFormDrawer({
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
          <EntityField
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

function EntityField({ disabled, field, onChange, value }) {
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
        // Se aceptan opciones como texto plano ("Matutina") o como par
        // {value,label}: las pantallas de listado usan lo primero y los
        // catalogos lo segundo, y no vale la pena forzar una sola forma.
        options={normalizeOptions(field.options)}
        placeholder="Seleccione una opcion"
        required={field.required}
        value={value ?? ""}
      />
    );
  }

  if (field.type === "file") {
    return (
      <FileField
        disabled={disabled}
        field={field}
        onChange={onChange}
        value={value}
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
      type={TEXT_INPUT_TYPES.has(field.type) ? field.type : "text"}
      value={value ?? ""}
    />
  );
}

/** Tipos que se delegan tal cual al input nativo. */
const TEXT_INPUT_TYPES = new Set(["number", "email", "tel", "date", "url", "password"]);

function normalizeOptions(options = []) {
  return options.map((option) =>
    typeof option === "string" ? { value: option, label: option } : option
  );
}

/**
 * Campo de archivo con vista previa de imagen.
 *
 * La URL del objeto se revoca al cambiar de archivo y al desmontar: sin eso
 * cada foto elegida queda retenida en memoria hasta recargar la pagina.
 */
function FileField({ disabled, field, onChange, value }) {
  const [previewUrl, setPreviewUrl] = useState(null);

  useEffect(() => {
    if (!(value instanceof File)) {
      setPreviewUrl(null);
      return undefined;
    }
    const objectUrl = URL.createObjectURL(value);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [value]);

  return (
    <Stack gap={1}>
      <Typography sx={{ fontSize: "0.75rem", color: "text.secondary" }}>
        {field.label}
      </Typography>
      <Stack alignItems="center" direction="row" gap={1.5}>
        <Button
          component="label"
          disabled={disabled}
          size="small"
          startIcon={<UploadFileIcon fontSize="small" />}
          variant="outlined"
        >
          {value instanceof File ? "Cambiar archivo" : "Elegir archivo"}
          <input
            accept={field.accept}
            hidden
            onChange={(event) => onChange(field.name, event.target.files[0] || null)}
            type="file"
          />
        </Button>
        <Typography color="text.secondary" sx={{ fontSize: "0.8125rem" }} noWrap>
          {value instanceof File ? value.name : "Ningun archivo seleccionado"}
        </Typography>
      </Stack>
      {previewUrl ? (
        <Box
          alt="Vista previa"
          component="img"
          src={previewUrl}
          sx={(theme) => ({
            width: 96,
            height: 96,
            objectFit: "cover",
            borderRadius: theme.tokens.radii.chip,
            border: "1px solid",
            borderColor: "divider",
          })}
        />
      ) : null}
      {field.help ? (
        <Typography color="text.secondary" sx={{ fontSize: "0.75rem" }}>
          {field.help}
        </Typography>
      ) : null}
    </Stack>
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
    } else if (field.type === "file") {
      // El File se pasa intacto: convertirlo a texto lo destruiria, y el
      // servicio necesita el binario para armar el FormData.
      payload[field.name] = value ?? null;
    } else {
      payload[field.name] = String(value ?? "").trim();
    }
  }

  return payload;
}
