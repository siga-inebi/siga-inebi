import { useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";

import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";

/** Formulario del expediente en línea, sin abrir otra ventana. */
export function RecordForm({
  fields,
  initialValues = {},
  onSubmit,
  onCancel,
  onBusy,
  submitLabel = "Guardar",
  title,
}) {
  const [values, setValues] = useState(initialValues);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault();
    if (busy) return;
    const missing = fields.find(
      (field) => field.required && !String(values[field.name] ?? "").trim()
    );
    if (missing) {
      setError(`Complete el campo ${missing.label.toLowerCase()}.`);
      return;
    }
    setBusy(true);
    onBusy?.(true);
    setError("");
    try {
      await onSubmit(values);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
      onBusy?.(false);
    }
  };
  return (
    <Box component="form" noValidate onSubmit={submit} aria-label={title}>
      <Stack gap={2}>
        {error ? <Alert severity="error">{error}</Alert> : null}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
            gap: 2,
          }}
        >
          {fields.map((field) => (
            <Box
              key={field.name}
              sx={field.span === "full" ? { gridColumn: "1 / -1" } : undefined}
            >
              {field.type === "file" ? (
                <label>
                  {field.label}
                  <input
                    aria-label={field.label}
                    type="file"
                    accept={field.accept}
                    disabled={busy}
                    onChange={(event) =>
                      setValues((current) => ({
                        ...current,
                        [field.name]: event.target.files[0] ?? null,
                      }))
                    }
                  />
                </label>
              ) : field.type === "select" ? (
                <FormSelect
                  fullWidth
                  label={field.label}
                  required={field.required}
                  options={field.options}
                  disabled={busy}
                  value={values[field.name] ?? ""}
                  onChange={(event) =>
                    setValues((current) => ({
                      ...current,
                      [field.name]: event.target.value,
                    }))
                  }
                />
              ) : (
                <FormTextField
                  fullWidth
                  label={field.label}
                  required={field.required}
                  disabled={busy}
                  type={
                    field.type === "textarea" ? "text" : (field.type ?? "text")
                  }
                  multiline={field.type === "textarea"}
                  minRows={field.type === "textarea" ? 3 : undefined}
                  value={values[field.name] ?? ""}
                  onChange={(event) =>
                    setValues((current) => ({
                      ...current,
                      [field.name]: event.target.value,
                    }))
                  }
                />
              )}
            </Box>
          ))}
        </Box>
        <Stack direction="row" gap={1}>
          <Button type="submit" variant="contained" disabled={busy}>
            {busy ? "Guardando…" : submitLabel}
          </Button>
          <Button disabled={busy} onClick={onCancel}>
            Cancelar
          </Button>
        </Stack>
      </Stack>
    </Box>
  );
}
