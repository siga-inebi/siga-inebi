import { useCallback, useEffect, useMemo, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import CircularProgress from "@mui/material/CircularProgress";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { enrolmentsService } from "@enrolments/enrolmentsService.js";
import { collectAllPages } from "@shared/api/pages.js";
import { BatchResultAlert } from "@shared/crud/BatchResultAlert.jsx";
import { useBatchSubmit } from "@shared/crud/useBatchSubmit.js";
import {
  sectionsForCycle,
  studentOption,
  useCycleCatalog,
  useSectionCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { useSearchableCatalog } from "@shared/catalogs/useSearchableCatalog.js";
import { studentsService } from "@students/studentsService.js";
import { EmptyState } from "@ui/feedback/EmptyState.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

/**
 * Matriculacion por lotes: una seccion, varios estudiantes.
 *
 * Matricular un grado entero de uno en uno son treinta y cinco formularios
 * identicos salvo el nombre. Aqui el ciclo, la seccion y la fecha se eligen una
 * vez y lo que se marca es a quien matricular.
 *
 * La lista solo ofrece a quien NO tiene matricula vigente en ese ciclo: el
 * backend rechaza la segunda, y mostrar candidatos imposibles solo produce
 * errores que la persona no provoco.
 *
 * El estudiante se busca por texto en el backend (`?search=`), no se trae el
 * catalogo completo para filtrar en el cliente: con miles de estudiantes esta
 * ventana pedia 4 paginas enteras solo para poder escribir un nombre. Por eso
 * la lista arranca vacia — hay que escribir para ver candidatos, no hay un
 * listado inicial que mostrar sin pedirlo entero.
 *
 * Cada alta va por separado — no hay endpoint de lote — y el cupo se valida del
 * lado del servidor: si la seccion se llena a mitad del lote, las que entraron
 * quedan y el resumen dice cuales no.
 */
export function BulkEnrolmentWindow({ onClose, onCreated }) {
  const cycles = useCycleCatalog();
  const sections = useSectionCatalog();

  const [cycleId, setCycleId] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [effectiveOn, setEffectiveOn] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState([]);
  // Etiqueta capturada al marcar, no al enviar: para cuando se envia el lote,
  // la busqueda ya pudo cambiar y el estudiante ya no estar entre los
  // resultados visibles, pero el resumen todavia necesita su nombre.
  const [selectedLabels, setSelectedLabels] = useState(new Map());

  const [enrolled, setEnrolled] = useState(null);
  const [loadingEnrolled, setLoadingEnrolled] = useState(false);
  const [loadError, setLoadError] = useState("");

  const students = useSearchableCatalog(
    "students",
    studentsService.listPage,
    studentOption,
    search
  );

  const sectionOptions = sectionsForCycle(sections.options, cycleId);
  const section = sectionOptions.find((option) => option.value === sectionId);

  const createOne = useCallback(
    (studentId) =>
      enrolmentsService.matriculate({
        student_id: studentId,
        academic_cycle_id: cycleId,
        grade_id: section.gradeId,
        shift_id: section.shiftId,
        section_id: sectionId,
        effective_on: effectiveOn,
      }),
    [cycleId, section, sectionId, effectiveOn]
  );
  const describe = useCallback(
    (studentId) => selectedLabels.get(studentId) ?? studentId,
    [selectedLabels]
  );
  const { run, reset, submitting, result } = useBatchSubmit(
    createOne,
    describe
  );

  // Quien ya tiene matricula vigente en el ciclo. Se relee al cambiar de ciclo
  // y despues de cada lote, porque el propio lote cambia la respuesta.
  useEffect(() => {
    if (!cycleId) {
      setEnrolled(null);
      return undefined;
    }

    let active = true;
    setLoadingEnrolled(true);
    setLoadError("");

    collectAllPages((params) => enrolmentsService.listActive(params))
      .then((rows) => {
        if (!active) return;
        setEnrolled(
          new Set(
            rows
              .filter((row) => row.academic_cycle_id === cycleId)
              .map((row) => row.student_id)
          )
        );
      })
      .catch((error) => {
        if (active) {
          setEnrolled(null);
          setLoadError(error.message);
        }
      })
      .finally(() => {
        if (active) setLoadingEnrolled(false);
      });

    return () => {
      active = false;
    };
  }, [cycleId, result]);

  const candidates = useMemo(() => {
    if (!enrolled) return [];
    return students.options.filter((student) => !enrolled.has(student.value));
  }, [enrolled, students.options]);

  const visibleIds = candidates.map((student) => student.value);
  const allVisibleSelected =
    visibleIds.length > 0 && visibleIds.every((id) => selected.includes(id));

  const rememberLabels = (rows) =>
    setSelectedLabels((current) => {
      const next = new Map(current);
      for (const row of rows) next.set(row.value, row.label);
      return next;
    });

  const toggle = (student) => {
    rememberLabels([student]);
    setSelected((current) =>
      current.includes(student.value)
        ? current.filter((id) => id !== student.value)
        : [...current, student.value]
    );
  };

  const toggleAllVisible = () => {
    rememberLabels(candidates);
    setSelected((current) =>
      allVisibleSelected
        ? current.filter((id) => !visibleIds.includes(id))
        : [...new Set([...current, ...visibleIds])]
    );
  };

  const handleSubmit = async () => {
    const summary = await run(selected);
    setSelected([]);
    if (summary.created.length > 0) {
      onCreated?.();
    }
  };

  const ready = Boolean(cycleId && sectionId && effectiveOn);

  return (
    <FloatingWindow
      busy={submitting}
      description="Elija la seccion una vez y marque a quien matricular. Solo aparecen los estudiantes sin matricula vigente en ese ciclo."
      footer={
        <>
          <Button disabled={submitting} onClick={onClose} variant="text">
            Cerrar
          </Button>
          <Button
            disabled={!ready || selected.length === 0 || submitting}
            onClick={handleSubmit}
            startIcon={submitting ? <CircularProgress size={16} /> : undefined}
            variant="contained"
          >
            {submitting
              ? "Matriculando…"
              : `Matricular ${selected.length} ${
                  selected.length === 1 ? "estudiante" : "estudiantes"
                }`}
          </Button>
        </>
      }
      onClose={onClose}
      open
      title="Matriculacion por lotes"
      width={WINDOW_WIDTH.wide}
    >
      <Stack gap={2.5}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "1fr 1fr 1fr" },
            gap: 2,
          }}
        >
          <FormSelect
            error={cycles.error}
            fullWidth
            label="Ciclo escolar"
            loading={cycles.loading}
            onChange={(event) => {
              setCycleId(event.target.value);
              setSectionId("");
              setSelected([]);
              reset();
            }}
            options={cycles.options}
            placeholder="Seleccione un ciclo"
            required
            value={cycleId}
          />
          <FormSelect
            disabled={!cycleId}
            error={sections.error}
            fullWidth
            helperText={
              section?.capacity
                ? `Cupo de la seccion: ${section.capacity}.`
                : !cycleId
                  ? "Elija primero el ciclo escolar."
                  : undefined
            }
            label="Seccion"
            loading={sections.loading}
            onChange={(event) => {
              setSectionId(event.target.value);
              reset();
            }}
            options={sectionOptions}
            placeholder="Seleccione una seccion"
            required
            value={sectionId}
          />
          <FormTextField
            helperText="Misma fecha para todo el lote."
            label="Vigente desde"
            onChange={(event) => setEffectiveOn(event.target.value)}
            required
            slotProps={{ inputLabel: { shrink: true } }}
            type="date"
            value={effectiveOn}
          />
        </Box>

        {loadError ? <Alert severity="error">{loadError}</Alert> : null}

        <BatchResultAlert noun="matricula" result={result} />

        {!ready ? (
          <Alert severity="info">
            Elija ciclo, seccion y fecha de vigencia para ver a los estudiantes
            disponibles.
          </Alert>
        ) : loadingEnrolled ? (
          <Stack alignItems="center" sx={{ py: 4 }}>
            <CircularProgress size={24} />
          </Stack>
        ) : (
          <Stack gap={1.5}>
            <Stack
              alignItems={{ xs: "stretch", sm: "center" }}
              direction={{ xs: "column", sm: "row" }}
              gap={1.5}
            >
              <SearchField
                onChange={setSearch}
                placeholder="Buscar por nombre o codigo (minimo 2 letras)…"
                value={search}
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={allVisibleSelected}
                    disabled={visibleIds.length === 0}
                    onChange={toggleAllVisible}
                  />
                }
                label={`Seleccionar los ${visibleIds.length} visibles`}
              />
              <Typography
                color="text.secondary"
                sx={{ fontSize: "0.8125rem", ml: { sm: "auto" } }}
              >
                {selected.length} seleccionado
                {selected.length === 1 ? "" : "s"}
              </Typography>
            </Stack>

            {!students.ready ? (
              <EmptyState message="Escriba al menos 2 letras del nombre o codigo para buscar." />
            ) : students.loading ? (
              <Stack alignItems="center" sx={{ py: 4 }}>
                <CircularProgress size={24} />
              </Stack>
            ) : candidates.length === 0 ? (
              <EmptyState
                message={
                  students.options.length === 0
                    ? "Ningun estudiante coincide con la busqueda."
                    : "Los estudiantes que coinciden ya tienen matricula vigente en este ciclo."
                }
              />
            ) : (
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 1,
                  maxHeight: "22rem",
                  overflowY: "auto",
                  px: 1.5,
                  py: 1,
                }}
              >
                {candidates.map((student) => (
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={selected.includes(student.value)}
                        onChange={() => toggle(student)}
                      />
                    }
                    key={student.value}
                    label={student.label}
                  />
                ))}
              </Box>
            )}
          </Stack>
        )}
      </Stack>
    </FloatingWindow>
  );
}
