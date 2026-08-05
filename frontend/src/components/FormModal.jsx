import { useEffect, useState } from "react";

import { useBodyScrollLock } from "../hooks/useBodyScrollLock.js";

function isEmpty(value) {
  return value == null || String(value).trim() === "";
}

function FilePreview({ file }) {
  const [url, setUrl] = useState(null);

  useEffect(() => {
    if (!file) {
      setUrl(null);
      return undefined;
    }
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);

  if (!url) {
    return null;
  }
  return <img alt="Vista previa" className="file-preview" src={url} />;
}

export function FormModal({
  fields,
  initialValues = {},
  onCancel,
  onSubmit,
  submitLabel = "Guardar",
  title,
}) {
  const [values, setValues] = useState(() =>
    Object.fromEntries(
      fields.map((field) => [field.name, initialValues[field.name] ?? ""])
    )
  );
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useBodyScrollLock();

  const handleChange = (name, value) => {
    setValues((current) => ({ ...current, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const missing = fields.find(
      (field) => field.required && isEmpty(values[field.name])
    );
    if (missing) {
      setError(`El campo "${missing.label}" es obligatorio.`);
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await onSubmit(values);
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <button
        aria-label="Cerrar"
        className="overlay-backdrop"
        onClick={onCancel}
        type="button"
      />
      <div aria-label={title} className="panel modal" role="dialog">
        <div className="modal-body">
          <h2>{title}</h2>
          {error ? (
            <div className="message message-error">{error}</div>
          ) : null}
          <form className="form" onSubmit={handleSubmit}>
            {fields.map((field) => (
              <label className="field" key={field.name}>
                <span>{field.label}</span>
                {field.type === "select" ? (
                  <select
                    onChange={(event) =>
                      handleChange(field.name, event.target.value)
                    }
                    value={values[field.name]}
                  >
                    <option value="">Seleccione...</option>
                    {field.options.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                ) : field.type === "file" ? (
                  <>
                    <input
                      accept={field.accept}
                      onChange={(event) =>
                        handleChange(field.name, event.target.files[0] || null)
                      }
                      type="file"
                    />
                    <FilePreview file={values[field.name]} />
                  </>
                ) : (
                  <input
                    onChange={(event) =>
                      handleChange(field.name, event.target.value)
                    }
                    placeholder={field.placeholder}
                    type={field.type || "text"}
                    value={values[field.name]}
                  />
                )}
              </label>
            ))}
            <div className="modal-actions">
              <button
                className="button secondary"
                onClick={onCancel}
                type="button"
              >
                Cancelar
              </button>
              <button className="button" disabled={submitting} type="submit">
                {submitting ? "Guardando..." : submitLabel}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  );
}
