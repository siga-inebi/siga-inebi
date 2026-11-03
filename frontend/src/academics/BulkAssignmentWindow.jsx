import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { academicsService } from "@academics/academicsService.js";
import { TEACHER_SEARCH, sectionSearch } from "@academics/searchOptions.js";
import { cyclesService } from "@cycles/cyclesService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { useCycleCatalog } from "@shared/catalogs/academicCatalogs.js";
import { BatchResultAlert } from "@shared/crud/BatchResultAlert.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { RemoteSearchSelect } from "@ui/forms/RemoteSearchSelect.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

/** Tope de una sola pagina: una seccion tiene a lo sumo una decena de cursos. */
const ONE_PAGE = 100;

function subjectLabel(subject) {
  return subject.code ? `${subject.name} (${subject.code})` : subject.name;
}

/**
 * Asignación docente por lotes: una sección, todos sus cursos de una vez (AD2).
 *
 * El ciclo, la sección y la fecha se eligen UNA vez y la ventana pregunta lo
 * único que cambia por fila: quién imparte cada curso. Los cursos salen del
 * plan de estudios del ciclo para el grado de la sección, y el docente vigente
 * de cada uno, del listado filtrado por esa sección: no se descargan
 * historiales completos para compararlos en el navegador.
 *
 * Los cursos que ya tienen docente vigente se muestran sin selector:
 * reasignar cierra la asignación anterior con fecha de corte, y esa decisión
 * se toma curso por curso desde el listado.
 *
 * El alta va en un solo `POST …/teaching-assignments/batch/`; el backend guarda
 * cada fila por separado y devuelve las creadas y las rechazadas con su motivo.
 */
export function BulkAssignmentWindow({ onClose, onCreated }) {
  const cycles = useCycleCatalog();

  const [cycleId, setCycleId] = useState("");
  const [section, setSection] = useState(null);
  const [startsOn, setStartsOn] = useState("");
  // Opcion de docente elegida por curso ({value, label}).
  const [choices, setChoices] = useState({});
  // Cambia cuando "Aplicar a todos" reescribe los selectores de las filas.
  const [applied, setApplied] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [submitError, setSubmitError] = useState("");

  const sectionId = section?.value ?? "";
  const gradeId = section?.gradeId ?? "";

  const sectionPicker = useMemo(() => {
    const base = sectionSearch(cycleId);
    return {
      ...base,
      mapResult: (row) => ({
        ...base.mapResult(row),
        gradeId: row.grade?.public_id,
      }),
    };
  }, [cycleId]);

  const planParams = {
    academic_cycle_id: cycleId,
    grade_id: gradeId,
    page_size: ONE_PAGE,
  };
  const plan = useQuery({
    queryKey: queryKeys.academics.list("curriculum-plans", planParams),
    queryFn: () => academicsService.listCurriculumPlans(planParams),
    enabled: Boolean(cycleId && gradeId),
  });

  const currentParams = {
    section_id: sectionId,
    current: true,
    page_size: ONE_PAGE,
  };
  const current = useQuery({
    queryKey: queryKeys.academics.teachingAssignments(currentParams),
    queryFn: () => academicsService.listTeachingAssignments(currentParams),
    enabled: Boolean(sectionId),
  });

  const subjects = (plan.data?.results ?? []).map((row) => row.subject);
  const assigned = useMemo(
    () =>
      new Map(
        (current.data?.results ?? []).map((row) => [
          row.subject_id,
          row.teacher?.name ?? "Docente sin nombre",
        ])
      ),
    [current.data]
  );

  const pending = subjects.filter(
    (subject) => !assigned.has(subject.public_id)
  );
  const chosen = pending.filter((subject) => choices[subject.public_id]);

  const resetRows = () => {
    setChoices({});
    setResult(null);
    setSubmitError("");
  };

  const applyToAllPending = (option) => {
    if (!option) return;
    setChoices((currentChoices) => {
      const next = { ...currentChoices };
      for (const subject of pending) next[subject.public_id] = option;
      return next;
    });
    setApplied((value) => value + 1);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setSubmitError("");
    try {
      const response = await cyclesService.createAssignmentsBatch(cycleId, {
        starts_on: startsOn,
        items: chosen.map((subject) => ({
          section_id: sectionId,
          subject_id: subject.public_id,
          teacher_id: choices[subject.public_id].value,
        })),
      });
      const names = new Map(
        subjects.map((subject) => [subject.public_id, subjectLabel(subject)])
      );
      setResult({
        created: response.created ?? [],
        failed: (response.failed ?? []).map((failure) => ({
          label: names.get(failure.subject_id) ?? "Curso",
          message: failure.detail,
        })),
      });
      setChoices({});
      setApplied((value) => value + 1);
      if ((response.created ?? []).length > 0) {
        current.refetch();
        onCreated?.();
      }
    } catch (requestError) {
      setSubmitError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    { key: "subject", label: "Curso", render: (row) => subjectLabel(row) },
    {
      key: "current",
      label: "Docente vigente",
      render: (row) =>
        assigned.has(row.public_id) ? (
          <Stack alignItems="center" direction="row" gap={1}>
            <StatusChip label="Asignado" variant="success" />
            <span>{assigned.get(row.public_id)}</span>
          </Stack>
        ) : (
          <MutedCell>Sin docente</MutedCell>
        ),
    },
    {
      key: "teacher",
      label: "Asignar a",
      render: (row) =>
        assigned.has(row.public_id) ? (
          <MutedCell>Reasigne desde el listado</MutedCell>
        ) : (
          <Box sx={{ minWidth: "16rem" }}>
            <RemoteSearchSelect
              initialOption={choices[row.public_id]}
              key={`${row.public_id}-${applied}`}
              label={`Docente para ${row.name}`}
              name={`teacher-${row.public_id}`}
              onChange={() => {}}
              onOptionChange={(option) =>
                setChoices((currentChoices) => ({
                  ...currentChoices,
                  [row.public_id]: option,
                }))
              }
              placeholder="Dejar sin asignar"
              search={TEACHER_SEARCH}
              value={choices[row.public_id]?.value ?? ""}
            />
          </Box>
        ),
    },
  ];

  const ready = Boolean(cycleId && sectionId && startsOn);
  const loadError = plan.error?.message || current.error?.message || "";

  return (
    <FloatingWindow
      busy={submitting}
      description="Elija la sección una vez y reparta sus cursos entre los docentes. Solo se dan de alta los cursos del plan de estudios que hoy no tienen docente vigente."
      footer={
        <>
          <Button disabled={submitting} onClick={onClose} variant="text">
            Cerrar
          </Button>
          <Button
            disabled={!ready || chosen.length === 0 || submitting}
            onClick={handleSubmit}
            startIcon={submitting ? <CircularProgress size={16} /> : undefined}
            variant="contained"
          >
            {submitting
              ? "Asignando…"
              : `Asignar ${chosen.length} ${chosen.length === 1 ? "curso" : "cursos"}`}
          </Button>
        </>
      }
      onClose={onClose}
      open
      title="Asignación docente por lotes"
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
              setSection(null);
              resetRows();
            }}
            options={cycles.options}
            placeholder="Seleccione un ciclo"
            required
            value={cycleId}
          />
          {cycleId ? (
            <RemoteSearchSelect
              key={`section-${cycleId}`}
              label="Sección"
              name="section_id"
              onChange={() => {}}
              onOptionChange={(option) => {
                setSection(option);
                resetRows();
              }}
              placeholder="Escriba el grado o la sección"
              required
              search={sectionPicker}
              value={sectionId}
            />
          ) : (
            <FormSelect
              disabled
              fullWidth
              helperText="Elija primero el ciclo escolar."
              label="Sección"
              options={[]}
              required
              value=""
            />
          )}
          <FormTextField
            helperText="Misma fecha para todas las asignaciones del lote."
            label="Vigente desde"
            onChange={(event) => setStartsOn(event.target.value)}
            required
            slotProps={{ inputLabel: { shrink: true } }}
            type="date"
            value={startsOn}
          />
        </Box>

        {loadError ? <Alert severity="error">{loadError}</Alert> : null}
        {submitError ? (
          <Alert role="alert" severity="error">
            {submitError}
          </Alert>
        ) : null}

        <BatchResultAlert
          noun="asignación"
          nounPlural="asignaciones"
          result={result}
        />

        {ready && !current.isPending && pending.length > 1 ? (
          <Stack
            alignItems={{ xs: "stretch", sm: "center" }}
            direction={{ xs: "column", sm: "row" }}
            gap={1.5}
          >
            <Typography color="text.secondary" sx={{ fontSize: "0.8125rem" }}>
              Atajo: el mismo docente para los {pending.length} cursos
              pendientes
            </Typography>
            <Box sx={{ minWidth: "18rem" }}>
              <RemoteSearchSelect
                key={`all-${applied}`}
                label="Aplicar a todos"
                name="apply_all"
                onChange={() => {}}
                onOptionChange={applyToAllPending}
                placeholder="Buscar docente"
                search={TEACHER_SEARCH}
                value=""
              />
            </Box>
          </Stack>
        ) : null}

        {!ready ? (
          <Alert severity="info">
            Elija ciclo, sección y fecha de vigencia para ver los cursos.
          </Alert>
        ) : (
          <DataTable
            columns={columns}
            emptyMessage="El grado de esta sección no tiene cursos en el plan de estudios del ciclo."
            getRowKey={(row) => row.public_id}
            loading={plan.isPending || current.isPending}
            rows={subjects}
          />
        )}
      </Stack>
    </FloatingWindow>
  );
}
