import { useEffect, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";

import { cyclesService } from "@cycles/cyclesService.js";
import { formatDate } from "@shared/utils/format.js";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

/** Anios ofrecidos: uno atras para registrar el ciclo en curso, y seis adelante. */
const YEARS_BACK = 1;
const YEARS_AHEAD = 6;

function yearOptions(now = new Date()) {
  const first = now.getFullYear() - YEARS_BACK;
  return Array.from(
    { length: YEARS_BACK + 1 + YEARS_AHEAD },
    (_unused, index) => {
      const year = first + index;
      return { value: String(year), label: String(year) };
    }
  );
}

/**
 * Alta y clonado de un ciclo escolar, con todo derivado del anio.
 *
 * El ciclo se elige por su ANIO. Su nombre es su anio ("Ciclo 2027") y su
 * vigencia sale del calendario guatemalteco, asi que pedir las tres cosas por
 * separado no le daba libertad a nadie: habilitaba un "Ciclo 2026" cuya columna
 * year dice 2027, y un dedazo en las fechas corre en silencio todas las reglas
 * que cuelgan del ciclo (vigencia de matriculas, asignaciones docentes,
 * porcentaje de asistencia).
 *
 * El anio se elige de una lista y no se teclea: es un valor de un rango chico y
 * conocido, y "2072" no se distingue de "2027" al leerlo de reojo.
 *
 * Las tres siguen siendo editables — un acuerdo ministerial puede mover el
 * calendario — pero cambiar el anio las vuelve a calcular: el anio es lo que las
 * determina, y dejar una fecha de 2027 debajo de un ciclo 2028 seria peor.
 *
 * La regla se consulta al backend en vez de duplicarse aca. Dos copias de la
 * misma regla en dos lenguajes es como se llega a que el formulario muestre una
 * fecha y el servidor guarde otra.
 */
export function CycleFormWindow({
  description,
  initialYear,
  onCancel,
  onSubmit,
  submitLabel,
  title,
  withAssignmentsToggle = false,
}) {
  const years = yearOptions();
  const [year, setYear] = useState(String(initialYear));
  const [values, setValues] = useState({
    name: "",
    starts_on: "",
    ends_on: "",
    description: "",
  });
  const [includeAssignments, setIncludeAssignments] = useState(false);

  const [loadingDefaults, setLoadingDefaults] = useState(true);
  const [defaultsError, setDefaultsError] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Los derivados se releen en cada cambio de anio. La descripcion NO se toca:
  // es texto institucional que alguien escribio, no un valor calculado.
  useEffect(() => {
    let active = true;
    setLoadingDefaults(true);
    setDefaultsError("");

    cyclesService
      .defaults(year)
      .then((defaults) => {
        if (!active) return;
        setValues((current) => ({
          ...current,
          name: defaults.name,
          starts_on: defaults.starts_on,
          ends_on: defaults.ends_on,
        }));
      })
      .catch((requestError) => {
        if (active) setDefaultsError(requestError.message);
      })
      .finally(() => {
        if (active) setLoadingDefaults(false);
      });

    return () => {
      active = false;
    };
  }, [year]);

  const setValue = (name, value) =>
    setValues((current) => ({ ...current, [name]: value }));

  const ready =
    values.name !== "" && values.starts_on !== "" && values.ends_on !== "";

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!ready || submitting) return;

    setSubmitting(true);
    setError("");
    try {
      await onSubmit({
        year: Number(year),
        name: values.name.trim(),
        starts_on: values.starts_on,
        ends_on: values.ends_on,
        description: values.description.trim(),
        ...(withAssignmentsToggle
          ? { include_teaching_assignments: includeAssignments }
          : null),
      });
    } catch (submitError) {
      // El mensaje se muestra SIN cerrar: cerrar en el error es como se pierde
      // lo que se acaba de llenar.
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
            disabled={submitting || loadingDefaults || !ready}
            onClick={handleSubmit}
            startIcon={submitting ? <CircularProgress size={16} /> : undefined}
            variant="contained"
          >
            {submitting ? "Guardando…" : submitLabel}
          </Button>
        </>
      }
      onClose={onCancel}
      open
      title={title}
      width={WINDOW_WIDTH.medium}
    >
      <Box component="form" noValidate onSubmit={handleSubmit}>
        <Stack gap={2.5}>
          {error ? (
            <Alert role="alert" severity="error">
              {error}
            </Alert>
          ) : null}
          {defaultsError ? (
            <Alert severity="warning">
              No se pudieron calcular las fechas del ciclo ({defaultsError}).
              Complete inicio y cierre a mano.
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
            <FormSelect
              fullWidth
              label="Ano del ciclo"
              onChange={(event) => setYear(event.target.value)}
              options={years}
              required
              value={year}
            />
            <FormTextField
              fullWidth
              helperText="Se deriva del ano; puede ajustarlo."
              label="Nombre del ciclo"
              onChange={(event) => setValue("name", event.target.value)}
              required
              value={values.name}
            />
            <FormTextField
              fullWidth
              helperText={
                values.starts_on
                  ? `Inicio: ${formatDate(values.starts_on)}`
                  : "Se deriva del ano."
              }
              label="Inicio"
              onChange={(event) => setValue("starts_on", event.target.value)}
              required
              slotProps={{ inputLabel: { shrink: true } }}
              type="date"
              value={values.starts_on}
            />
            <FormTextField
              fullWidth
              helperText={
                values.ends_on
                  ? `Cierre: ${formatDate(values.ends_on)}`
                  : "Se deriva del ano."
              }
              label="Cierre"
              onChange={(event) => setValue("ends_on", event.target.value)}
              required
              slotProps={{ inputLabel: { shrink: true } }}
              type="date"
              value={values.ends_on}
            />
            <Box sx={{ gridColumn: { sm: "1 / -1" } }}>
              <FormTextField
                fullWidth
                label="Descripcion (opcional)"
                onChange={(event) =>
                  setValue("description", event.target.value)
                }
                value={values.description}
              />
            </Box>
          </Box>

          {withAssignmentsToggle ? (
            <FormControlLabel
              control={
                <Switch
                  checked={includeAssignments}
                  disabled={submitting}
                  onChange={(event) =>
                    setIncludeAssignments(event.target.checked)
                  }
                />
              }
              label="Copiar tambien las asignaciones docentes"
            />
          ) : null}
        </Stack>
      </Box>
    </FloatingWindow>
  );
}
