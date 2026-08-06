import { useId, useState } from "react";

/**
 * Formulario de alta y edicion del catalogo.
 *
 * Los campos se describen con `{ name, label, type, help, required, options }`.
 * El codigo de cada recurso es inmutable en el backend, asi que las pantallas
 * simplemente no lo incluyen al editar.
 *
 * `onSubmit` recibe los valores ya normalizados y puede rechazar: el mensaje
 * del backend se muestra sin cerrar el formulario, para no perder lo escrito.
 */
export function CatalogueForm({
  title,
  description,
  fields,
  initialValues,
  submitLabel = "Guardar",
  onSubmit,
  onCancel,
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
    <form className="catalogue-form panel" onSubmit={handleSubmit}>
      <h3>{title}</h3>
      {description ? <p className="muted">{description}</p> : null}
      {error ? (
        <div className="message message-error" role="alert">
          {error}
        </div>
      ) : null}

      <div className="form-grid">
        {fields.map((field) => (
          <FormField
            field={field}
            inputId={`${formId}-${field.name}`}
            key={field.name}
            onChange={setValue}
            value={values[field.name]}
          />
        ))}
      </div>

      <div className="actions">
        <button className="button" disabled={submitting} type="submit">
          {submitting ? "Guardando..." : submitLabel}
        </button>
        <button
          className="button secondary"
          disabled={submitting}
          onClick={onCancel}
          type="button"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}

/**
 * La etiqueta se asocia por `htmlFor` en vez de envolver al control: asi el
 * nombre accesible del campo es solo su etiqueta y la ayuda no se le pega.
 */
function FormField({ field, inputId, value, onChange }) {
  const help = field.help ? (
    <small className="muted">{field.help}</small>
  ) : null;

  if (field.type === "checkbox") {
    return (
      <div className="field field-inline">
        <input
          checked={Boolean(value)}
          id={inputId}
          name={field.name}
          onChange={(event) => onChange(field.name, event.target.checked)}
          type="checkbox"
        />
        <label htmlFor={inputId}>{field.label}</label>
        {help}
      </div>
    );
  }

  if (field.type === "select") {
    return (
      <div className="field">
        <label htmlFor={inputId}>{field.label}</label>
        <select
          id={inputId}
          name={field.name}
          onChange={(event) => onChange(field.name, event.target.value)}
          value={value ?? ""}
        >
          <option value="">Seleccione una opcion</option>
          {field.options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {help}
      </div>
    );
  }

  return (
    <div className="field">
      <label htmlFor={inputId}>{field.label}</label>
      <input
        id={inputId}
        min={field.type === "number" ? field.min : undefined}
        name={field.name}
        onChange={(event) => onChange(field.name, event.target.value)}
        placeholder={field.placeholder}
        type={field.type === "number" ? "number" : "text"}
        value={value ?? ""}
      />
      {help}
    </div>
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
