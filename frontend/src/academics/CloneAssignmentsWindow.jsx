import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { TEACHER_SEARCH, sectionLabel } from "@academics/searchOptions.js";
import { cyclesService } from "@cycles/cyclesService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { useCycleCatalog } from "@shared/catalogs/academicCatalogs.js";
import { BatchResultAlert } from "@shared/crud/BatchResultAlert.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { DateField } from "@ui/forms/DateField.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { RemoteSearchSelect } from "@ui/forms/RemoteSearchSelect.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

/** Estado de cada fila de la vista previa, como lo devuelve el backend. */
const CLONE_STATUS = {
  pending: { label: "Pendiente", variant: "primary" },
  already_assigned: { label: "Ya asignada", variant: "neutral" },
  unmatched: { label: "Sin sección equivalente", variant: "warning" },
};

const cellKey = (sectionId, subjectId) => `${sectionId}|${subjectId}`;

/**
 * Clona las asignaciones vigentes de un ciclo en otro, para confirmar (AD2).
 *
 * La comparación la hace el backend
 * (`GET cycles/<destino>/teaching-assignments/clone-preview/`): empareja las
 * secciones por grado, jornada y nombre (los identificadores cambian al clonar
 * la estructura) y marca cada fila como pendiente, ya asignada o sin sección
 * equivalente. La ventana no descarga historiales para compararlos.
 *
 * Nada se guarda hasta confirmar. Ahí se cambia lo que cambió (el docente que
 * se fue) o se quita el docente para no clonar esa fila. Las pendientes
 * elegidas se envían en un solo lote, y el resultado dice cuáles entraron y
 * cuáles no, con su motivo.
 */
export function CloneAssignmentsWindow({ onClose, onCreated }) {
  const cycles = useCycleCatalog();

  const [sourceCycleId, setSourceCycleId] = useState("");
  const [targetCycleId, setTargetCycleId] = useState("");
  const [startsOn, setStartsOn] = useState("");
  // Docente elegido por fila pendiente: {value, label} o null para no clonarla.
  const [choices, setChoices] = useState({});
  const [done, setDone] = useState(() => new Set());
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);
  const [submitError, setSubmitError] = useState("");

  const sameCycle = sourceCycleId !== "" && sourceCycleId === targetCycleId;
  const enabled = Boolean(sourceCycleId && targetCycleId && !sameCycle);

  const preview = useQuery({
    queryKey: [
      ...queryKeys.academics.cycle(targetCycleId),
      "clone-preview",
      sourceCycleId,
    ],
    queryFn: () =>
      cyclesService.cloneAssignmentsPreview(targetCycleId, sourceCycleId),
    enabled,
  });
  const data = enabled ? preview.data : undefined;

  // Al llegar una vista previa nueva se proponen los docentes del origen y la
  // fecha sugerida (inicio del ciclo destino, o hoy si ya empezó).
  useEffect(() => {
    if (!data) return;
    setChoices(
      Object.fromEntries(
        data.results
          .filter((row) => row.status === "pending" && row.teacher)
          .map((row) => [
            row.source_assignment_id,
            { value: row.teacher.public_id, label: row.teacher.name },
          ])
      )
    );
    setDone(new Set());
    setResult(null);
    if (data.suggested_starts_on) setStartsOn(data.suggested_starts_on);
  }, [data]);

  const rows = data?.results ?? [];
  const statusOf = (row) =>
    row.status === "pending" &&
    row.target_section &&
    done.has(cellKey(row.target_section.public_id, row.subject?.public_id))
      ? "already_assigned"
      : row.status;
  const pending = rows.filter((row) => statusOf(row) === "pending");
  const chosen = pending.filter((row) => choices[row.source_assignment_id]);
  const unmatched = rows.filter((row) => row.status === "unmatched");

  const handleSubmit = async () => {
    setSubmitting(true);
    setSubmitError("");
    try {
      const response = await cyclesService.createAssignmentsBatch(
        targetCycleId,
        {
          starts_on: startsOn,
          items: chosen.map((row) => ({
            section_id: row.target_section.public_id,
            subject_id: row.subject.public_id,
            teacher_id: choices[row.source_assignment_id].value,
          })),
        }
      );
      const created = response.created ?? [];
      const describe = new Map(
        chosen.map((row) => [
          cellKey(row.target_section.public_id, row.subject.public_id),
          `${sectionLabel(row.target_section)} · ${row.subject.name}`,
        ])
      );
      setResult({
        created,
        failed: (response.failed ?? []).map((failure) => ({
          label:
            describe.get(cellKey(failure.section_id, failure.subject_id)) ??
            "Asignación",
          message: failure.detail,
        })),
      });
      setDone(
        (current) =>
          new Set([
            ...current,
            ...created.map((row) => cellKey(row.section_id, row.subject_id)),
          ])
      );
      if (created.length > 0) onCreated?.();
    } catch (requestError) {
      setSubmitError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    {
      key: "section",
      label: "Sección",
      render: (row) => sectionLabel(row.section ?? {}),
    },
    {
      key: "subject",
      label: "Curso",
      render: (row) => row.subject?.name ?? "Curso",
    },
    {
      key: "previous",
      label: "Docente del ciclo de origen",
      render: (row) => <MutedCell>{row.teacher?.name ?? "Docente"}</MutedCell>,
    },
    {
      key: "status",
      label: "Estado",
      render: (row) => {
        const status = CLONE_STATUS[statusOf(row)] ?? {
          label: row.status,
          variant: "neutral",
        };
        return <StatusChip label={status.label} variant={status.variant} />;
      },
    },
    {
      key: "teacher",
      label: "Se asignará a",
      render: (row) =>
        statusOf(row) !== "pending" ? null : (
          <Box sx={{ minWidth: "16rem" }}>
            <RemoteSearchSelect
              initialOption={choices[row.source_assignment_id] ?? undefined}
              label="Docente"
              name={`teacher-${row.source_assignment_id}`}
              onChange={() => {}}
              onOptionChange={(option) =>
                setChoices((current) => ({
                  ...current,
                  [row.source_assignment_id]: option,
                }))
              }
              placeholder="No clonar esta fila"
              search={TEACHER_SEARCH}
              value={choices[row.source_assignment_id]?.value ?? ""}
            />
          </Box>
        ),
    },
  ];

  const ready = enabled && Boolean(startsOn);
  const summary = data?.summary;

  return (
    <FloatingWindow
      busy={submitting}
      description="Trae las asignaciones vigentes de un ciclo y las propone para otro. Nada se guarda hasta confirmar: revise los cambios del año antes de aplicar."
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
              : `Clonar ${chosen.length} ${chosen.length === 1 ? "asignación" : "asignaciones"}`}
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
            helperText="Misma fecha para todas; se propone la que sugiere el ciclo destino."
            label="Vigente desde"
            onChange={(event) => setStartsOn(event.target.value)}
            required
            value={startsOn}
          />
        </Box>

        {enabled && preview.error ? (
          <Alert severity="error">{preview.error.message}</Alert>
        ) : null}
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

        {summary ? (
          <Typography color="text.secondary" variant="body2">
            {summary.total} vigentes en el origen · {summary.pending} pendientes
            · {summary.already_assigned} ya asignadas · {summary.unmatched} sin
            sección equivalente
          </Typography>
        ) : null}

        {unmatched.length > 0 ? (
          <Alert severity="info">
            {unmatched.length}{" "}
            {unmatched.length === 1
              ? "asignación no tiene"
              : "asignaciones no tienen"}{" "}
            sección equivalente en el ciclo destino. Clone primero la estructura
            del ciclo (oferta de grados y secciones) o cree la sección para
            poder traerlas.
          </Alert>
        ) : null}

        {!enabled ? (
          <Alert severity="info">
            Elija el ciclo de origen y el ciclo destino para ver la propuesta.
          </Alert>
        ) : (
          <DataTable
            columns={columns}
            emptyMessage="El ciclo de origen no tiene asignaciones vigentes que traer."
            getRowKey={(row) => row.source_assignment_id}
            loading={preview.isPending}
            rows={rows}
          />
        )}
      </Stack>
    </FloatingWindow>
  );
}
