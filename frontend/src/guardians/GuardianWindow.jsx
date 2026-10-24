import { lazy, Suspense, useId, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";

import { EntityFields } from "@shared/crud/EntityFormWindow.jsx";
import { DetailField } from "@ui/layout/DetailWindow.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

const GuardianStudentsSection = lazy(() =>
  import("./GuardianStudentsSection.jsx").then((module) => ({
    default: module.GuardianStudentsSection,
  }))
);

/**
 * Ficha única del encargado: datos, edición en el mismo lugar y estudiantes
 * vinculados. Antes eran tres ventanas que se reemplazaban una a otra y la
 * persona perdía de vista a quién estaba editando o vinculando.
 *
 * @param {object}   props
 * @param {object}   props.guardian
 * @param {Array}    props.fields      Datos que muestra la ficha `{label, value}`.
 * @param {Array}    props.editFields  Campos declarativos del modo edición.
 * @param {Function} props.editValues  `(guardian) => valores iniciales`.
 * @param {Function} props.onSave      Recibe los valores; puede rechazar.
 * @param {Function} [props.onDeactivate] Sin ella no se ofrece desactivar.
 * @param {Function} props.onClose
 */
export function GuardianWindow({
  editFields,
  editValues,
  fields,
  guardian,
  onClose,
  onDeactivate,
  onSave,
  title,
}) {
  const formId = useId();
  const [editing, setEditing] = useState(false);
  const [values, setValues] = useState({});
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [linking, setLinking] = useState(false);
  const busy = saving || linking;

  const startEditing = () => {
    setValues(editValues(guardian));
    setError("");
    setEditing(true);
  };
  const submit = async (event) => {
    event.preventDefault();
    const missing = editFields.find(
      (field) => field.required && !String(values[field.name] ?? "").trim()
    );
    if (missing) {
      setError(`Complete el campo ${missing.label.toLowerCase()}.`);
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSave(
        Object.fromEntries(
          Object.entries(values).map(([name, value]) => [
            name,
            String(value ?? "").trim(),
          ])
        )
      );
    } catch (failure) {
      setError(failure.message);
      setSaving(false);
      return;
    }
    setSaving(false);
    setEditing(false);
  };

  return (
    <FloatingWindow
      busy={busy}
      footer={
        editing ? (
          <>
            {/* Claves distintas a las del modo lectura: si React reutilizara el
                boton "Editar" como submit, el mismo clic enviaria el formulario. */}
            <Button
              disabled={saving}
              key="cancel"
              onClick={() => setEditing(false)}
            >
              Cancelar
            </Button>
            <Button
              disabled={saving}
              form={formId}
              key="save"
              startIcon={saving ? <CircularProgress size={16} /> : undefined}
              type="submit"
              variant="contained"
            >
              {saving ? "Guardando…" : "Guardar cambios"}
            </Button>
          </>
        ) : (
          <>
            {onDeactivate ? (
              <Button
                color="error"
                key="deactivate"
                disabled={busy}
                onClick={onDeactivate}
                variant="outlined"
              >
                Desactivar encargado
              </Button>
            ) : null}
            <Button
              disabled={busy}
              key="edit"
              onClick={startEditing}
              variant="contained"
            >
              Editar
            </Button>
          </>
        )
      }
      onClose={() => {
        if (!busy) onClose();
      }}
      open
      title={editing ? `Editar ${title}` : title}
      width={WINDOW_WIDTH.wide}
    >
      {editing ? (
        <Box component="form" id={formId} noValidate onSubmit={submit}>
          {error ? (
            <Alert role="alert" severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          ) : null}
          <EntityFields
            disabled={saving}
            fields={editFields}
            onChange={(name, value) =>
              setValues((current) => ({ ...current, [name]: value }))
            }
            values={values}
          />
        </Box>
      ) : (
        <>
          <Box
            component="dl"
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
              gap: 2.5,
              m: 0,
            }}
          >
            {fields.map((field) => (
              <DetailField
                key={field.label}
                label={field.label}
                value={field.value}
              />
            ))}
          </Box>
          <Suspense
            fallback={<p role="status">Preparando estudiantes vinculados…</p>}
          >
            <GuardianStudentsSection guardian={guardian} onBusy={setLinking} />
          </Suspense>
        </>
      )}
    </FloatingWindow>
  );
}
