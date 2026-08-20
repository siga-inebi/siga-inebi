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
import { DateField } from "@ui/forms/DateField.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

const SKIP = "";

/** Una seccion se reconoce entre ciclos por grado + jornada + nombre, no por id. */
const sectionKey = (option) =>
  `${option.gradeId}|${option.shiftId}|${option.name}`;

/**
 * Clona la configuracion docente de un ciclo al siguiente, para confirmar.
 *
 * Armar el horario de un ciclo son decenas de asignaciones, y de un ano al
 * siguiente casi todas se repiten: el mismo docente, la misma seccion, el mismo
 * curso. Volver a capturarlas una por una era el trabajo mas largo del arranque
 * de ciclo, y el mas facil de equivocar por cansancio.
 *
 * Clonar NO guarda nada por si solo: trae la configuracion del ciclo anterior,
 * la muestra ya resuelta y espera la confirmacion. Ahi es donde se cambia lo que
 * cambio — el docente que se fue, el curso que ya no se imparte — que es
 * exactamente lo que un clonado ciego se lleva puesto.
 *
 * El emparejamiento de secciones es por grado, jornada y nombre. Los
 * identificadores cambian al clonar la estructura del ciclo, asi que apuntar al
 * id de la seccion del ano pasado no encontraria nada; "Primero Basico A de la
 * matutina" sigue significando lo mismo.
 *
 * Cada alta se envia por separado porque el backend no publica un endpoint de
 * lote; que una falle no cancela las demas, y el resumen dice cuales quedaron
 * pendientes en vez de dejar el ciclo a medias sin explicar que paso.
 */
export function CloneAssignmentsWindow({ onClose, onCreated }) {
  const cycles = useCycleCatalog();
  const sections = useSectionCatalog();
  const subjects = useSubjectCatalog();
  const teachers = useTeacherCatalog();

  const [sourceCycleId, setSourceCycleId] = useState("");
  const [targetCycleId, setTargetCycleId] = useState("");
  const [startsOn, setStartsOn] = useState("");
  const [choices, setChoices] = useState({});

  const [plan, setPlan] = useState(null);
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [loadError, setLoadError] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const names = useMemo(
    () => ({
      subjects: new Map(subjects.options.map((o) => [o.value, o.label])),
      teachers: new Map(teachers.options.map((o) => [o.value, o.label])),
      sections: new Map(sections.options.map((o) => [o.value, o.label])),
    }),
    [subjects.options, teachers.options, sections.options]
  );

  // La vigencia propuesta es el inicio del ciclo destino: una asignacion que
  // arranca antes de que el ciclo abra la rechaza el backend.
  const targetCycle = cycles.options.find(
    (option) => option.value === targetCycleId
  );
  useEffect(() => {
    if (targetCycle?.startsOn) setStartsOn(targetCycle.startsOn);
  }, [targetCycle?.startsOn]);

  // Lee las asignaciones vigentes del ciclo origen y las traduce a las secciones
  // equivalentes del destino, marcando lo que ya esta asignado alla.
  useEffect(() => {
    if (!sourceCycleId || !targetCycleId || sections.loading) {
      setPlan(null);
      return undefined;
    }

    let active = true;
    setLoadingPlan(true);
    setLoadError("");
    setResult(null);

    Promise.all([
      collectAllPages((params) =>
        academicsService.listTeachingAssignmentHistory({
          ...params,
          academic_cycle_id: sourceCycleId,
        })
      ),
      collectAllPages((params) =>
        academicsService.listTeachingAssignmentHistory({
          ...params,
          academic_cycle_id: targetCycleId,
        })
      ),
    ])
      .then(([sourceHistory, targetHistory]) => {
        if (!active) return;

        const targetByKey = new Map(
          sectionsForCycle(sections.options, targetCycleId).map((option) => [
            sectionKey(option),
            option,
          ])
        );
        const sourceById = new Map(
          sectionsForCycle(sections.options, sourceCycleId).map((option) => [
            option.value,
            option,
          ])
        );
        const alreadyThere = new Set(
          targetHistory
            .filter((row) => !row.ends_on)
            .map((row) => `${row.section_id}|${row.subject_id}`)
        );

        const rows = sourceHistory
          .filter((row) => !row.ends_on)
          .map((row) => {
            const sourceSection = sourceById.get(row.section_id);
            const targetSection = sourceSection
              ? targetByKey.get(sectionKey(sourceSection))
              : undefined;
            return {
              id: `${row.section_id}|${row.subject_id}`,
              sectionLabel:
                names.sections.get(row.section_id) ?? "Seccion desconocida",
              subjectId: row.subject_id,
              teacherId: row.teacher_id,
              targetSectionId: targetSection?.value ?? null,
              assigned: targetSection
                ? alreadyThere.has(`${targetSection.value}|${row.subject_id}`)
                : false,
            };
          });

        setPlan(rows);
        setChoices(
          Object.fromEntries(rows.map((row) => [row.id, row.teacherId]))
        );
      })
      .catch((error) => {
        if (active) {
          setPlan(null);
          setLoadError(error.message);
        }
      })
      .finally(() => {
        if (active) setLoadingPlan(false);
      });

    return () => {
      active = false;
    };
  }, [sourceCycleId, targetCycleId, sections.loading, sections.options, names]);

  const sameCycle = sourceCycleId !== "" && sourceCycleId === targetCycleId;
  const pending = (plan ?? []).filter(
    (row) => row.targetSectionId && !row.assigned
  );
  const chosen = pending.filter((row) => (choices[row.id] ?? SKIP) !== SKIP);
  const orphans = (plan ?? []).filter((row) => !row.targetSectionId);

  const applyToAll = (teacherId) =>
    setChoices((current) => {
      const next = { ...current };
      for (const row of pending) next[row.id] = teacherId;
      return next;
    });

  const handleSubmit = async () => {
    setSubmitting(true);
    setResult(null);

    const created = [];
    const failed = [];

    for (const row of chosen) {
      const label = `${row.sectionLabel} · ${names.subjects.get(row.subjectId) ?? "Curso"}`;
      try {
        await academicsService.createTeachingAssignment({
          academic_cycle_id: targetCycleId,
          section_id: row.targetSectionId,
          subject_id: row.subjectId,
          teacher_id: choices[row.id],
          starts_on: startsOn,
        });
        created.push(row.id);
      } catch (error) {
        failed.push({ label, message: error.message });
      }
    }

    setSubmitting(false);
    setResult({ created: created.length, failed });

    if (created.length > 0) {
      // Lo creado deja de estar pendiente: se marca sin cerrar la ventana, para
      // que el resumen y la tabla cuenten la misma historia.
      const done = new Set(created);
      setPlan((current) =>
        (current ?? []).map((row) =>
          done.has(row.id) ? { ...row, assigned: true } : row
        )
      );
      onCreated?.();
    }
  };

  const columns = [
    { key: "section", label: "Seccion", render: (row) => row.sectionLabel },
    {
      key: "subject",
      label: "Curso",
      render: (row) => names.subjects.get(row.subjectId) ?? "Curso",
    },
    {
      key: "previous",
      label: "Docente del ciclo anterior",
      render: (row) => (
        <MutedCell>{names.teachers.get(row.teacherId) ?? "Docente"}</MutedCell>
      ),
    },
    {
      key: "teacher",
      label: "Se asignara a",
      render: (row) => {
        if (!row.targetSectionId) {
          return <MutedCell>Sin seccion equivalente</MutedCell>;
        }
        if (row.assigned) {
          return <StatusChip label="Ya asignado" variant="neutral" />;
        }
        return (
          // Sin etiqueta propia (la columna ya dice "Se asignara a") y con ancho
          // minimo: el nombre completo del docente es el dato que hay que leer
          // para decidir, y truncado a "An..." la confirmacion no sirve de nada.
          <FormSelect
            fullWidth
            loading={teachers.loading}
            onChange={(event) =>
              setChoices((current) => ({
                ...current,
                [row.id]: event.target.value,
              }))
            }
            options={teachers.options}
            placeholder="No clonar esta"
            sx={{ minWidth: "16rem" }}
            value={choices[row.id] ?? SKIP}
          />
        );
      },
    },
  ];

  const ready = sourceCycleId && targetCycleId && !sameCycle && startsOn;

  return (
    <FloatingWindow
      busy={submitting}
      description="Trae las asignaciones vigentes de un ciclo y las propone para el nuevo. Nada se guarda hasta confirmar: revise los cambios del ano antes de aplicar."
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
              ? "Clonando…"
              : `Clonar ${chosen.length} ${chosen.length === 1 ? "asignacion" : "asignaciones"}`}
          </Button>
        </>
      }
      onClose={onClose}
      open
      title="Clonar asignaciones en un ciclo nuevo"
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
            label="Copiar desde"
            loading={cycles.loading}
            onChange={(event) => setSourceCycleId(event.target.value)}
            options={cycles.options}
            placeholder="Ciclo de origen"
            required
            value={sourceCycleId}
          />
          <FormSelect
            error={cycles.error}
            fullWidth
            helperText={
              sameCycle ? "Elija un ciclo distinto al de origen." : undefined
            }
            label="Copiar hacia"
            loading={cycles.loading}
            onChange={(event) => setTargetCycleId(event.target.value)}
            options={cycles.options}
            placeholder="Ciclo nuevo"
            required
            value={targetCycleId}
          />
          <DateField
            fullWidth
            helperText="Misma fecha para todas; se propone el inicio del ciclo."
            label="Vigente desde"
            onChange={(event) => setStartsOn(event.target.value)}
            required
            value={startsOn}
          />
        </Box>

        {loadError ? <Alert severity="error">{loadError}</Alert> : null}

        {result ? (
          <Alert severity={result.failed.length > 0 ? "warning" : "success"}>
            <Stack gap={0.5}>
              <span>
                {result.created} asignacion{result.created === 1 ? "" : "es"}{" "}
                creada{result.created === 1 ? "" : "s"}.
              </span>
              {result.failed.map((failure) => (
                <span key={failure.label}>
                  {failure.label}: {failure.message}
                </span>
              ))}
            </Stack>
          </Alert>
        ) : null}

        {orphans.length > 0 ? (
          <Alert severity="info">
            {orphans.length} asignacion{orphans.length === 1 ? "" : "es"} sin
            seccion equivalente en el ciclo nuevo. Clone primero la estructura
            del ciclo (oferta de grados y secciones) para poder traerlas.
          </Alert>
        ) : null}

        {ready && !loadingPlan && pending.length > 1 ? (
          <Stack
            alignItems={{ xs: "stretch", sm: "center" }}
            direction={{ xs: "column", sm: "row" }}
            gap={1.5}
          >
            <Typography color="text.secondary" sx={{ fontSize: "0.8125rem" }}>
              Atajo: el mismo docente para las {pending.length} asignaciones
            </Typography>
            <FormSelect
              label="Aplicar a todas"
              loading={teachers.loading}
              onChange={(event) => applyToAll(event.target.value)}
              options={teachers.options}
              placeholder="Sin aplicar"
              sx={{ minWidth: "18rem" }}
              value=""
            />
          </Stack>
        ) : null}

        {!ready ? (
          <Alert severity="info">
            Elija el ciclo de origen, el ciclo nuevo y la fecha de vigencia.
          </Alert>
        ) : (
          <DataTable
            columns={columns}
            emptyMessage="El ciclo de origen no tiene asignaciones vigentes que traer."
            getRowKey={(row) => row.id}
            loading={loadingPlan || subjects.loading}
            rows={plan ?? []}
          />
        )}
      </Stack>
    </FloatingWindow>
  );
}
