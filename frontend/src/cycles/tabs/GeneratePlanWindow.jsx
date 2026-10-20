import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import LinearProgress from "@mui/material/LinearProgress";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { academicsService } from "@academics/academicsService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

/** Un grado no lleva mas de unas decenas de cursos: una pagina alcanza. */
const MAX = 100;

const STATUS = {
  created: ["Agregado", "success"],
  failed: ["No se agregó", "danger"],
  saving: ["Agregando…", "primary"],
};

/**
 * "Generar desde cursos del nivel" (docs/ux-ui.md N2): propone los cursos del
 * nivel del grado que todavía no están en el plan del ciclo y los agrega uno
 * por uno, con avance y el motivo de cada rechazo. El backend valida cada
 * alta; aquí solo se compara qué falta.
 */
export function GeneratePlanWindow({
  cycleId,
  grades,
  initialGradeId,
  onClose,
}) {
  const [gradeId, setGradeId] = useState(initialGradeId ?? "");
  const [results, setResults] = useState({});
  const [running, setRunning] = useState(false);
  // Al generar se congela la lista: cada alta invalida la cache y la lista
  // recalculada ya no mostraria lo recien agregado ni su resultado.
  const [snapshot, setSnapshot] = useState(null);
  const grade = grades.find((option) => option.value === gradeId);

  const candidates = useQuery({
    queryKey: [
      ...queryKeys.academics.list("plan-candidates", cycleId),
      gradeId,
    ],
    enabled: Boolean(grade?.levelId),
    queryFn: async () => {
      const [levelSubjects, plans] = await Promise.all([
        academicsService.listLevelSubjects(grade.levelId, { page_size: MAX }),
        academicsService.listCurriculumPlans({
          academic_cycle_id: cycleId,
          grade_id: gradeId,
          page_size: MAX,
        }),
      ]);
      const planned = new Set(
        (plans.results ?? []).map((plan) => plan.subject?.public_id)
      );
      return (levelSubjects.results ?? []).filter(
        (link) => link.subject && !planned.has(link.subject.public_id)
      );
    },
  });

  const missing = snapshot ?? candidates.data ?? [];
  const pending = missing.filter(
    (link) => results[link.subject.public_id]?.status !== "created"
  );
  const done = Object.values(results).filter(
    (result) => result.status === "created"
  ).length;
  const processed = Object.values(results).filter(
    (result) => result.status !== "saving"
  ).length;

  const generate = async () => {
    setRunning(true);
    setSnapshot(missing);
    // Uno por uno: un rechazo no detiene a los demás y cada fila dice el suyo.
    for (const link of pending) {
      const subjectId = link.subject.public_id;
      setResults((current) => ({
        ...current,
        [subjectId]: { status: "saving" },
      }));
      try {
        await academicsService.createCurriculumPlan({
          academic_cycle_id: cycleId,
          grade_id: gradeId,
          subject_id: subjectId,
          is_required: link.is_required ?? true,
        });
        setResults((current) => ({
          ...current,
          [subjectId]: { status: "created" },
        }));
      } catch (error) {
        setResults((current) => ({
          ...current,
          [subjectId]: { status: "failed", detail: error.message },
        }));
      }
    }
    setRunning(false);
  };

  return (
    <FloatingWindow
      busy={running}
      description="Agrega al plan de este ciclo los cursos del nivel que todavía no tiene el grado elegido."
      footer={
        <>
          <Button disabled={running} onClick={onClose} variant="text">
            {done > 0 ? "Cerrar" : "Cancelar"}
          </Button>
          <Button
            disabled={running || !grade || pending.length === 0}
            onClick={generate}
            variant="contained"
          >
            {running
              ? "Agregando…"
              : `Agregar ${pending.length} ${pending.length === 1 ? "curso" : "cursos"}`}
          </Button>
        </>
      }
      onClose={running ? undefined : onClose}
      open
      title="Generar desde cursos del nivel"
      width={WINDOW_WIDTH.medium}
    >
      <Stack gap={2}>
        <FormSelect
          disabled={running}
          fullWidth
          label="Grado"
          onChange={(event) => {
            setGradeId(event.target.value);
            setResults({});
            setSnapshot(null);
          }}
          options={grades}
          placeholder="Seleccione un grado"
          value={gradeId}
        />
        {candidates.error ? (
          <Alert severity="error">{candidates.error.message}</Alert>
        ) : null}
        {running || processed > 0 ? (
          <Stack gap={0.5}>
            <LinearProgress
              value={missing.length ? (processed / missing.length) * 100 : 0}
              variant="determinate"
            />
            <Typography role="status" variant="body2">
              Agregados {done} de {missing.length}.
            </Typography>
          </Stack>
        ) : null}
        {!grade ? (
          <Typography color="text.secondary" variant="body2">
            Elija un grado para ver qué cursos de su nivel faltan en el plan.
          </Typography>
        ) : candidates.isPending ? (
          <Typography role="status" variant="body2">
            Comparando con los cursos del nivel…
          </Typography>
        ) : missing.length === 0 ? (
          <Alert severity="success">
            El plan de {grade.name} ya tiene todos los cursos de{" "}
            {grade.levelName ?? "su nivel"}.
          </Alert>
        ) : (
          <List dense disablePadding>
            {missing.map((link) => {
              const result = results[link.subject.public_id];
              const [label, variant] = STATUS[result?.status] ?? [];
              return (
                <ListItem
                  disableGutters
                  key={link.subject.public_id}
                  secondaryAction={
                    label ? (
                      <StatusChip label={label} variant={variant} />
                    ) : null
                  }
                >
                  <ListItemText
                    primary={link.subject.name}
                    secondary={
                      result?.detail ??
                      [
                        link.is_required === false ? "Optativo" : "Obligatorio",
                        link.weekly_hours != null
                          ? `${link.weekly_hours} h semanales`
                          : null,
                      ]
                        .filter(Boolean)
                        .join(" · ")
                    }
                    slotProps={{
                      secondary: result?.detail
                        ? { color: "error.main" }
                        : undefined,
                    }}
                  />
                </ListItem>
              );
            })}
          </List>
        )}
      </Stack>
    </FloatingWindow>
  );
}
