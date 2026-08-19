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

import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";

/**
 * Formulario de alta y edicion en ventana modal centrada.
 *
 * Conserva el contrato declarativo de campos que ya usaban las pantallas
 * (`{ name, label, type, help, required, options, min, placeholder, span }`),
 * asi que migrar una pantalla no obliga a reescribir su definicion de campos.
 *
 * Los campos `select` aceptan ademas `loading`, `optionsError` y `emptyHint`
 * para los catalogos que se traen del backend: mientras cargan el desplegable
 * se muestra deshabilitado y no vacio, porque un select sin opciones se lee
 * como "no hay nada" y esa es otra respuesta.
 *
 * `fields` tambien puede ser una funcion `(values) => campos` cuando un campo
 * depende de otro (las secciones de un ciclo, por ejemplo). Ese campo declara
 * `resets: ["section_id"]` para limpiar lo que quedo colgando al cambiar: una
 * seccion del ciclo anterior seguiria seleccionada y el backend la rechazaria
 * recien al guardar.
 *
 * Los campos se acomodan en dos columnas desde `sm`. Un campo puede pedir el
 * ancho completo con `span: "full"`; los de tipo archivo y los interruptores lo
 * toman siempre, porque partirlos a media reja los deja ilegibles.
 *
 * `onSubmit` recibe los valores ya normalizados y puede rechazar: el mensaje del
 * backend se muestra SIN cerrar la ventana, para no perder lo escrito. Cerrar en
 * el error es como se pierde media hora de captura.
 */
export function EntityFormWindow({
  description,
  fields,
  initialValues,
  onCancel,
  onSubmit,
  open,
  submitLabel = "Guardar",
  title,
  width = WINDOW_WIDTH.medium,
}) {
  const [values, setValues] = useState(initialValues);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Dos formularios pueden convivir en la pantalla (nivel y grado, por
  // ejemplo); el prefijo evita que compartan el id de un campo homonimo.
  const formId = useId();

  // Un campo puede depender de otro, asi que la lista se resuelve contra los
  // valores actuales en cada render.
  const resolvedFields = typeof fields === "function" ? fields(values) : fields;

  const setValue = (name, value) =>
    setValues((current) => {
      const field = resolvedFields.find((candidate) => candidate.name === name);
      const cleared = Object.fromEntries(
        (field?.resets ?? []).map((dependent) => [dependent, ""])
      );
      return { ...current, ...cleared, [name]: value };
    });

  const handleSubmit = async (event) => {
    event.preventDefault();

    const missing = resolvedFields.find(
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
      await onSubmit(normalize(resolvedFields, values));
    } catch (submitError) {
      setError(submitError.message);
      setSubmitting(false);
    }
  };

  return (
    <FloatingWindow
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
      width={width}
    >
      {/* El submit vive en el pie de la ventana, fuera del <form>: se enlazan
          por el atributo form/id, que es el mecanismo estandar para eso. */}
      <Box component="form" id={formId} noValidate onSubmit={handleSubmit}>
        {error ? (
          <Alert role="alert" severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        ) : null}

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
            columnGap: 2,
            rowGap: 2.5,
          }}
        >
          {resolvedFields.map((field) => (
            <Box
              key={field.name}
              sx={{
                gridColumn: isFullWidth(field) ? { sm: "1 / -1" } : undefined,
              }}
            >
              <EntityField
                disabled={submitting}
                field={field}
                onChange={setValue}
                value={values[field.name]}
              />
            </Box>
          ))}
        </Box>
      </Box>
    </FloatingWindow>
  );
}

/** Campos que nunca se parten a media reja. */
function isFullWidth(field) {
  return (
    field.span === "full" || field.type === "file" || field.type === "checkbox"
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
    const options = normalizeOptions(field.options);
    // Un catalogo vacio no es un error del formulario, es un dato que falta en
    // otra pantalla; decirlo ahi mismo evita que la persona busque el problema
    // en lo que acaba de escribir.
    const empty = !field.loading && options.length === 0;

    return (
      <FormSelect
        disabled={disabled || field.loading || empty}
        error={field.optionsError}
        fullWidth
        helperText={empty ? (field.emptyHint ?? field.help) : field.help}
        label={field.label}
        loading={field.loading}
        name={field.name}
        onChange={(event) => onChange(field.name, event.target.value)}
        // Se aceptan opciones como texto plano ("Matutina") o como par
        // {value,label}: las pantallas de listado usan lo primero y los
        // catalogos lo segundo, y no vale la pena forzar una sola forma.
        options={options}
        placeholder={field.placeholder ?? "Seleccione una opcion"}
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
      slotProps={{
        ...(field.type === "number" && field.min != null
          ? { htmlInput: { min: field.min } }
          : null),
        // Los inputs de fecha y hora SIEMPRE pintan su propio placeholder
        // ("mm/dd/yyyy"), asi que la etiqueta flotante se le encima si no se
        // fuerza arriba desde el principio.
        ...(DATE_LIKE_TYPES.has(field.type)
          ? { inputLabel: { shrink: true } }
          : null),
      }}
      type={TEXT_INPUT_TYPES.has(field.type) ? field.type : "text"}
      value={value ?? ""}
    />
  );
}

/** Tipos que traen placeholder propio del navegador. */
const DATE_LIKE_TYPES = new Set(["date", "datetime-local", "time"]);

/** Tipos que se delegan tal cual al input nativo. */
const TEXT_INPUT_TYPES = new Set([
  "number",
  "email",
  "tel",
  "date",
  "datetime-local",
  "time",
  "url",
  "password",
]);

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
  const inputId = useId();

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
      {/*
        Etiqueta real asociada por `htmlFor`, no un texto con aspecto de
        etiqueta: sin esto el nombre accesible del input seria el del boton
        ("Elegir archivo") y nadie sabria QUE archivo se esta pidiendo.
      */}
      <Typography
        component="label"
        htmlFor={inputId}
        sx={{ fontSize: "0.75rem", color: "text.secondary" }}
      >
        {field.label}
      </Typography>
      <Stack alignItems="center" direction="row" gap={1.5}>
        <Button
          component="label"
          disabled={disabled}
          htmlFor={inputId}
          size="small"
          startIcon={<UploadFileIcon fontSize="small" />}
          variant="outlined"
        >
          {value instanceof File ? "Cambiar archivo" : "Elegir archivo"}
          <input
            accept={field.accept}
            hidden
            id={inputId}
            onChange={(event) =>
              onChange(field.name, event.target.files[0] || null)
            }
            type="file"
          />
        </Button>
        <Typography
          color="text.secondary"
          sx={{ fontSize: "0.8125rem" }}
          noWrap
        >
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
