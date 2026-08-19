import { useEffect, useMemo, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { academicsService } from "@academics/academicsService.js";
import { collectAllPages } from "@shared/api/pages.js";
import {
  sectionsForCycle,
  useCycleCatalog,
  useSectionCatalog,
  useSubjectCatalog,
  useTeacherCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

const SIN_ASIGNAR = "";

/**
 * Asignacion docente por lotes: una seccion, todos sus cursos de una vez.
 *
 * Armar el horario de una seccion son ocho asignaciones, y hacerlas de una en
 * una obliga a repetir ciclo, seccion y fecha ocho veces para cambiar un solo
 * dato. Aqui el ciclo, la seccion y la fecha se eligen UNA vez y la ventana
 * pregunta lo unico que cambia por fila: quien da cada curso.
 *
 * Los cursos que ya tienen docente vigente se muestran, pero no se pueden
 * reasignar desde aqui: reasignar cierra la asignacion anterior y abre otra con
 * una fecha de corte, que es una decision por curso y no algo que deba pasar de
 * refilon dentro de una carga masiva.
 *
 * Cada alta se envia por separado porque el backend no publica un endpoint de
 * lote; que una falle no cancela las demas, y el resumen dice exactamente cuales
 * quedaron pendientes en vez de dejar a medias sin explicar que paso.
 */
export function BulkAssignmentWindow({ onClose, onCreated }) {
  const cycles = useCycleCatalog();
  const sections = useSectionCatalog();
  const subjects = useSubjectCatalog();
  const teachers = useTeacherCatalog();

  const [cycleId, setCycleId] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [startsOn, setStartsOn] = useState("");
  const [choices, setChoices] = useState({});

  const [assigned, setAssigned] = useState(null);
  const [loadingAssigned, setLoadingAssigned] = useState(false);
  const [loadError, setLoadError] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const sectionOptions = sectionsForCycle(sections.options, cycleId);
  const teacherNames = useMemo(
    () =>
      new Map(teachers.options.map((option) => [option.value, option.label])),
    [teachers.options]
  );

  // Docente vigente por curso en la seccion elegida. Se recorre el historial
  // completo porque el backend no publica un listado de asignaciones vigentes;
  // `ends_on` vacio es lo que distingue una vigente de una cerrada.
  useEffect(() => {
    if (!cycleId || !sectionId) {
      setAssigned(null);
      return undefined;
    }

    let active = true;
    setLoadingAssigned(true);
    setLoadError("");

    collectAllPages((params) =>
      academicsService.listTeachingAssignmentHistory({
        ...params,
        academic_cycle_id: cycleId,
      })
    )
      .then((history) => {
        if (!active) return;
        const current = new Map();
        for (const row of history) {
          if (row.section_id === sectionId && !row.ends_on) {
            current.set(row.subject_id, row.teacher_id);
          }
        }
        setAssigned(current);
      })
      .catch((error) => {
        if (active) {
          setAssigned(null);
          setLoadError(error.message);
        }
      })
      .finally(() => {
        if (active) setLoadingAssigned(false);
      });

    return () => {
      active = false;
    };
  }, [cycleId, sectionId]);

  const pending = subjects.options.filter(
    (subject) => !assigned?.has(subject.value)
  );
  const chosen = pending.filter(
    (subject) => (choices[subject.value] ?? SIN_ASIGNAR) !== SIN_ASIGNAR
  );

  const applyToAllPending = (teacherId) => {
    setChoices((current) => {
      const next = { ...current };
      for (const subject of pending) {
        next[subject.value] = teacherId;
      }
      return next;
    });
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setResult(null);

    const created = [];
    const failed = [];

    for (const subject of chosen) {
      try {
        await academicsService.createTeachingAssignment({
          academic_cycle_id: cycleId,
          section_id: sectionId,
          subject_id: subject.value,
          teacher_id: choices[subject.value],
          starts_on: startsOn,
        });
        created.push(subject.label);
      } catch (error) {
        failed.push({ subject: subject.label, message: error.message });
      }
    }

    setSubmitting(false);
    setResult({ created, failed });
    setChoices({});

    if (created.length > 0) {
      // Las asignaciones nuevas ya no son pendientes: se relee para que la
      // tabla lo refleje sin cerrar la ventana.
      setAssigned((current) => {
        const next = new Map(current);
        for (const subject of chosen) {
          if (created.includes(subject.label)) {
            next.set(subject.value, choices[subject.value]);
          }
        }
        return next;
      });
      onCreated?.();
    }
  };

  const columns = [
    { key: "subject", label: "Curso", render: (row) => row.label },
    {
      key: "current",
      label: "Docente vigente",
      render: (row) =>
        assigned?.has(row.value) ? (
          <Stack alignItems="center" direction="row" gap={1}>
            <StatusChip label="Asignado" variant="success" />
            <span>
              {teacherNames.get(assigned.get(row.value)) ??
                "Docente sin nombre"}
            </span>
          </Stack>
        ) : (
          <MutedCell>Sin docente</MutedCell>
        ),
    },
    {
      key: "teacher",
      label: "Asignar a",
      render: (row) =>
        assigned?.has(row.value) ? (
          <MutedCell>Reasigne desde el listado</MutedCell>
        ) : (
          <FormSelect
            fullWidth
            label="Docente"
            loading={teachers.loading}
            onChange={(event) =>
              setChoices((current) => ({
                ...current,
                [row.value]: event.target.value,
              }))
            }
            options={teachers.options}
            placeholder="Dejar sin asignar"
            value={choices[row.value] ?? SIN_ASIGNAR}
          />
        ),
    },
  ];

  const ready = cycleId && sectionId && startsOn;

  return (
    <FloatingWindow
      busy={submitting}
      description="Elija la seccion una vez y reparta sus cursos entre los docentes. Solo se dan de alta los cursos que hoy no tienen docente vigente."
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
      title="Asignacion docente por lotes"
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
              setChoices({});
              setResult(null);
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
              cycleId && !sections.loading && sectionOptions.length === 0
                ? "Ese ciclo no tiene secciones registradas."
                : !cycleId
                  ? "Elija primero el ciclo escolar."
                  : undefined
            }
            label="Seccion"
            loading={sections.loading}
            onChange={(event) => {
              setSectionId(event.target.value);
              setChoices({});
              setResult(null);
            }}
            options={sectionOptions}
            placeholder="Seleccione una seccion"
            required
            value={sectionId}
          />
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

        {result ? (
          <Alert severity={result.failed.length > 0 ? "warning" : "success"}>
            <Stack gap={0.5}>
              <span>
                {result.created.length} asignacion
                {result.created.length === 1 ? "" : "es"} creada
                {result.created.length === 1 ? "" : "s"}.
              </span>
              {result.failed.map((failure) => (
                <span key={failure.subject}>
                  {failure.subject}: {failure.message}
                </span>
              ))}
            </Stack>
          </Alert>
        ) : null}

        {ready && !loadingAssigned && pending.length > 1 ? (
          <Stack
            alignItems={{ xs: "stretch", sm: "center" }}
            direction={{ xs: "column", sm: "row" }}
            gap={1.5}
          >
            <Typography color="text.secondary" sx={{ fontSize: "0.8125rem" }}>
              Atajo: el mismo docente para los {pending.length} cursos
              pendientes
            </Typography>
            <FormSelect
              label="Aplicar a todos"
              loading={teachers.loading}
              onChange={(event) => applyToAllPending(event.target.value)}
              options={teachers.options}
              placeholder="Sin aplicar"
              sx={{ minWidth: "18rem" }}
              value=""
            />
          </Stack>
        ) : null}

        {!ready ? (
          <Alert severity="info">
            Elija ciclo, seccion y fecha de vigencia para ver los cursos.
          </Alert>
        ) : (
          <DataTable
            columns={columns}
            emptyMessage="Esta seccion ya tiene docente en todos sus cursos."
            getRowKey={(row) => row.value}
            loading={loadingAssigned || subjects.loading}
            rows={assigned ? subjects.options : []}
          />
        )}
      </Stack>
    </FloatingWindow>
  );
}
