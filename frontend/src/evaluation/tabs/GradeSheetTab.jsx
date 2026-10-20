import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { evaluationService } from "@evaluation/evaluationService.js";
import {
  defaultUnit,
  sectionOptions,
  unitLabel,
  useCycleSections,
  useCycleUnits,
  usePlanSubjects,
  useUrlParams,
} from "@evaluation/evaluationData.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { formatDate, formatDateTime } from "@shared/utils/format.js";
import { ConfirmDialog } from "@ui/feedback/ConfirmDialog.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";

/** Texto de una nota tal como la muestra la celda ("" sin nota). */
const asText = (grade) =>
  (grade?.value ?? "") === "" ? "" : String(grade.value);

/**
 * Valida una celda antes de enviar: entero de 0 a 100. El backend vuelve a
 * validar todo el lote; esto solo evita un viaje por un error evidente.
 */
function cellError(text, original) {
  if (text === "") {
    return original === ""
      ? ""
      : "No se puede dejar vacía una nota ya registrada.";
  }
  if (!/^\d{1,3}$/.test(text) || Number(text) > 100) {
    return "Escriba un número entero de 0 a 100.";
  }
  return "";
}

function readOnlyReason({ canWrite, sheet, unit }) {
  // can_capture ya incluye un permiso excepcional vigente del docente al que
  // se atribuye la nota (RF-EVC-004): en ese caso se edita aunque la ventana
  // esté cerrada o la unidad cerrada.
  if (sheet.unit.can_capture) {
    return canWrite
      ? ""
      : "Su cuenta puede consultar la planilla, pero no registrar notas.";
  }
  if (sheet.unit.status === "closed") {
    return "La unidad está cerrada: la planilla es de solo consulta.";
  }
  if (!sheet.unit.window_open) {
    return unit
      ? `La ventana de captura de «${unit.name}» va del ${formatDate(unit.capture_starts_on)} al ${formatDate(unit.capture_ends_on)}: hoy la planilla es de solo consulta.`
      : "La ventana de captura de esta unidad no está abierta: la planilla es de solo consulta.";
  }
  if (!canWrite) {
    return "Su cuenta puede consultar la planilla, pero no registrar notas.";
  }
  return "";
}

/**
 * Grilla editable de una planilla ya cargada. Se monta de nuevo (key) al cambiar
 * unidad, sección o subárea, así lo escrito nunca se cruza de una a otra.
 */
function SheetEditor({
  canWrite,
  cycleId,
  onDirtyChange,
  sheet,
  unit,
  unitId,
}) {
  const [edits, setEdits] = useState({});
  const [rowErrors, setRowErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const inputs = useRef([]);

  const rows = sheet.rows;
  const original = (row) => asText(row.grade);
  const valueOf = (row) => edits[row.enrolment_id] ?? original(row);
  const changed = rows.filter((row) => valueOf(row) !== original(row));
  const dirty = changed.length > 0;
  const lockedReason = readOnlyReason({ canWrite, sheet, unit });
  const editable = !lockedReason;
  const exceptionUntil =
    !sheet.unit.window_open && sheet.unit.capture_exception_expires_at
      ? sheet.unit.capture_exception_expires_at
      : null;

  useEffect(() => {
    onDirtyChange(dirty);
  }, [dirty, onDirtyChange]);

  // Cerrar la pestaña o recargar con cambios sin guardar pide confirmación.
  useEffect(() => {
    if (!dirty) return undefined;
    const warn = (event) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  const setCell = (row, text) => {
    setEdits((current) => ({ ...current, [row.enrolment_id]: text.trim() }));
    setRowErrors((current) => {
      if (!current[row.enrolment_id]) return current;
      const next = { ...current };
      delete next[row.enrolment_id];
      return next;
    });
    setNotice("");
  };

  // Enter y flecha abajo bajan a la siguiente fila; flecha arriba sube.
  const handleKeyDown = (event, index) => {
    const step =
      event.key === "Enter" || event.key === "ArrowDown"
        ? 1
        : event.key === "ArrowUp"
          ? -1
          : 0;
    if (step === 0) return;
    event.preventDefault();
    inputs.current[index + step]?.focus();
    inputs.current[index + step]?.select?.();
  };

  const save = async () => {
    const local = Object.fromEntries(
      changed
        .map((row) => [
          row.enrolment_id,
          cellError(valueOf(row), original(row)),
        ])
        .filter(([, message]) => message)
    );
    if (Object.keys(local).length > 0) {
      setRowErrors(local);
      setError("Corrija las notas marcadas antes de guardar.");
      return;
    }
    setSaving(true);
    setError("");
    setRowErrors({});
    try {
      const result = await evaluationService.saveSheet(cycleId, unitId, {
        section_id: sheet.section.public_id,
        subject_id: sheet.subject.public_id,
        grades: changed.map((row) => ({
          enrolment_id: row.enrolment_id,
          value: Number(valueOf(row)),
        })),
      });
      setEdits({});
      setNotice(
        `Se guardaron ${result.created + result.updated} notas (${result.created} nuevas, ${result.updated} corregidas).`
      );
    } catch (requestError) {
      const errors = requestError.payload?.errors;
      if (Array.isArray(errors) && errors.length > 0) {
        // `index` es la posición en el lote enviado, no en la planilla.
        setRowErrors(
          Object.fromEntries(
            errors
              .filter((item) => changed[item.index])
              .map((item) => [changed[item.index].enrolment_id, item.message])
          )
        );
        setError(
          "No se guardó ninguna nota: corrija las filas marcadas y vuelva a guardar."
        );
      } else {
        setError(requestError.message);
      }
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    {
      key: "number",
      label: "N.º",
      align: "right",
      render: (row) => rows.indexOf(row) + 1,
    },
    {
      key: "code",
      label: "Código",
      render: (row) => row.student.student_code,
    },
    {
      key: "student",
      label: "Estudiante",
      render: (row) => row.student.full_name,
    },
    {
      key: "value",
      label: "Nota (0–100)",
      align: "right",
      render: (row) => {
        const index = rows.indexOf(row);
        const message = rowErrors[row.enrolment_id];
        const isChanged = valueOf(row) !== original(row);
        return (
          <TextField
            disabled={!editable || saving}
            error={Boolean(message)}
            helperText={message || (isChanged ? "Sin guardar" : " ")}
            inputRef={(node) => {
              inputs.current[index] = node;
            }}
            onChange={(event) => setCell(row, event.target.value)}
            onKeyDown={(event) => handleKeyDown(event, index)}
            size="small"
            slotProps={{
              htmlInput: {
                "aria-label": `Nota de ${row.student.full_name}`,
                inputMode: "numeric",
                maxLength: 3,
                style: { textAlign: "right" },
              },
            }}
            sx={{ width: 120 }}
            value={valueOf(row)}
          />
        );
      },
    },
  ];

  return (
    <Stack gap={2}>
      <Stack
        alignItems={{ sm: "center" }}
        direction={{ xs: "column", sm: "row" }}
        gap={1}
        justifyContent="space-between"
      >
        <Typography variant="body2">
          <strong>Docente:</strong>{" "}
          {sheet.teacher?.name ?? "Sin docente asignado"}
          <Typography
            color="text.secondary"
            component="span"
            sx={{ ml: 1 }}
            variant="body2"
          >
            (de la asignación vigente de la sección y la subárea)
          </Typography>
        </Typography>
        <Typography color="text.secondary" variant="body2">
          {rows.length} estudiantes · {rows.filter((row) => row.grade).length}{" "}
          con nota
        </Typography>
      </Stack>

      {!sheet.teacher ? (
        <Alert severity="warning">
          La sección no tiene docente asignado en esta subárea, así que no se
          pueden guardar notas. Asígnelo en Ciclo escolar › Asignaciones.
        </Alert>
      ) : null}
      {lockedReason ? <Alert severity="info">{lockedReason}</Alert> : null}
      {exceptionUntil ? (
        <Alert severity="warning">
          La ventana de captura está cerrada, pero un permiso excepcional
          habilita la captura hasta el {formatDateTime(exceptionUntil)}.
        </Alert>
      ) : null}
      {notice ? (
        <Alert role="status" severity="success">
          {notice}
        </Alert>
      ) : null}
      {error ? (
        <Alert role="alert" severity="error">
          {error}
        </Alert>
      ) : null}

      <SectionTableArea>
        <DataTable
          columns={columns}
          emptyMessage="La sección no tiene matrículas activas."
          getRowKey={(row) => row.enrolment_id}
          rows={rows}
        />
      </SectionTableArea>

      {editable ? (
        <Stack direction="row" gap={1} justifyContent="flex-end">
          <Button
            disabled={!dirty || saving}
            onClick={() => {
              setEdits({});
              setRowErrors({});
              setError("");
            }}
          >
            Descartar cambios
          </Button>
          <Button
            disabled={!dirty || saving}
            onClick={save}
            variant="contained"
          >
            {saving
              ? "Guardando…"
              : dirty
                ? `Guardar cambios (${changed.length})`
                : "Guardar cambios"}
          </Button>
        </Stack>
      ) : null}
    </Stack>
  );
}

/**
 * Planilla de calificaciones (docs/ux-ui.md V2 y V8): unidad, sección y
 * subárea abren una tabla con una celda por estudiante. Se guarda en un solo
 * lote con lo que cambió; el docente sale de la asignación vigente y no se
 * elige a mano. El error de una fila vuelve a su fila.
 */
export function GradeSheetTab({ cycle }) {
  const cycleId = cycle.public_id;
  const { can } = usePermissions();
  const [params, setParams] = useUrlParams();
  const [dirty, setDirty] = useState(false);
  const [pending, setPending] = useState(null);

  const units = useCycleUnits(cycleId);
  const sections = useCycleSections(cycleId);
  const unitList = units.data ?? [];
  const unit =
    unitList.find((item) => item.public_id === params.get("unidad")) ??
    defaultUnit(unitList);
  const sectionId = params.get("seccion") ?? "";
  const section = (sections.data ?? []).find(
    (item) => item.public_id === sectionId
  );
  const subjects = usePlanSubjects(cycleId, section?.grade?.public_id);
  const subjectId = params.get("subarea") ?? "";

  const ready = Boolean(unit && section && subjectId);
  const sheet = useQuery({
    queryKey: queryKeys.evaluation(
      cycleId,
      "sheet",
      unit?.public_id,
      sectionId,
      subjectId
    ),
    queryFn: () =>
      evaluationService.getSheet(cycleId, unit.public_id, sectionId, subjectId),
    enabled: ready,
  });

  // Cambiar la selección con notas sin guardar pide confirmación.
  const change = (changes) => {
    if (dirty) setPending(changes);
    else setParams(changes);
  };

  return (
    <Stack gap={2}>
      <FilterBar>
        <FilterSelect
          label="Unidad"
          loading={units.isPending}
          minWidth={200}
          onChange={(value) => change({ unidad: value })}
          options={unitList.map((item) => ({
            value: item.public_id,
            label: unitLabel(item),
          }))}
          value={unit?.public_id ?? ""}
        />
        <FilterSelect
          emptyLabel="Elija una sección"
          label="Sección"
          loading={sections.isPending}
          minWidth={240}
          onChange={(value) => change({ seccion: value, subarea: "" })}
          options={sectionOptions(sections.data)}
          value={section ? sectionId : ""}
        />
        <FilterSelect
          emptyLabel={section ? "Elija una subárea" : "Elija antes la sección"}
          label="Subárea"
          loading={Boolean(section) && subjects.isPending}
          minWidth={220}
          onChange={(value) => change({ subarea: value })}
          options={subjects.data ?? []}
          value={
            subjects.data?.some((item) => item.value === subjectId)
              ? subjectId
              : ""
          }
        />
      </FilterBar>

      <SectionCard
        subtitle="Escriba la nota y pase a la siguiente con Enter o con las flechas. Solo se envía lo que cambió."
        title="Planilla de calificaciones"
      >
        <Stack sx={{ p: { xs: 1.5, md: 2 } }}>
          {units.isSuccess && unitList.length === 0 ? (
            <Typography color="text.secondary" variant="body2">
              Este ciclo no tiene unidades de evaluación. Créelas en la pestaña
              Unidades.
            </Typography>
          ) : !ready ? (
            <Typography color="text.secondary" variant="body2">
              Elija la unidad, la sección y la subárea para abrir su planilla.
            </Typography>
          ) : sheet.error ? (
            <Alert severity="error">{sheet.error.message}</Alert>
          ) : !sheet.data ? (
            <Typography role="status">Cargando planilla…</Typography>
          ) : (
            <SheetEditor
              canWrite={can(PERMISSION.GRADE_WRITE)}
              cycleId={cycleId}
              key={`${unit.public_id}-${sectionId}-${subjectId}`}
              onDirtyChange={setDirty}
              sheet={sheet.data}
              unit={unit}
              unitId={unit.public_id}
            />
          )}
        </Stack>
      </SectionCard>

      <ConfirmDialog
        confirmColor="error"
        confirmText="Descartar cambios"
        message="Hay notas escritas que no se guardaron. Si cambia de planilla se perderán."
        onClose={() => setPending(null)}
        onConfirm={() => {
          setDirty(false);
          setParams(pending);
          setPending(null);
        }}
        open={Boolean(pending)}
        title="¿Descartar los cambios?"
      />
    </Stack>
  );
}
