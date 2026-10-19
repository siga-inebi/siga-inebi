import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { enrolmentsService } from "@enrolments/enrolmentsService.js";
import {
  evaluationService,
  SUBJECT_CONDITION_LABEL,
  SUBJECT_CONDITION_VARIANT,
} from "@evaluation/evaluationService.js";
import {
  useCycleUnits,
  usePlanSubjects,
  useUrlParams,
} from "@evaluation/evaluationData.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { studentOption } from "@shared/catalogs/academicCatalogs.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { formatDateTime } from "@shared/utils/format.js";
import { studentsService } from "@students/studentsService.js";
import { RowActionsMenu } from "@ui/buttons/RowActionsMenu.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { RemoteSearchSelect } from "@ui/forms/RemoteSearchSelect.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

const STUDENT_SEARCH = Object.freeze({
  name: "students",
  fetchPage: (params) => studentsService.listPage(params),
  mapResult: studentOption,
});

const STAGE_LABEL = {
  live: "Durante el ciclo",
  post_freeze: "Después del cierre",
};

function ConditionChip({ condition }) {
  if (!condition) return <MutedCell>Sin calificar</MutedCell>;
  return (
    <StatusChip
      label={SUBJECT_CONDITION_LABEL[condition] ?? condition}
      variant={SUBJECT_CONDITION_VARIANT[condition] ?? "neutral"}
    />
  );
}

/** Matrícula del estudiante en el ciclo; prefiere la activa. */
function enrolmentInCycle(page, cycleId) {
  const inCycle = (page?.results ?? []).filter(
    (item) =>
      (item.academic_cycle?.public_id ?? item.academic_cycle_id) === cycleId
  );
  return inCycle.find((item) => item.status === "active") ?? inCycle[0] ?? null;
}

/** Trazabilidad del resultado de una subárea (RF-RES-009). */
function TraceWindow({ enrolmentId, onClose, subject }) {
  const trace = useQuery({
    queryKey: queryKeys.audit.all.concat(
      "result-trace",
      enrolmentId,
      subject.id
    ),
    queryFn: () => evaluationService.getResultTrace(enrolmentId, subject.id),
  });
  const data = trace.data;
  return (
    <FloatingWindow
      description="Notas de unidad, recuperación y correcciones con su motivo y autor."
      footer={<Button onClick={onClose}>Cerrar</Button>}
      onClose={onClose}
      open
      title={`Trazabilidad de ${subject.name}`}
    >
      {trace.error ? (
        <Alert severity="error">{trace.error.message}</Alert>
      ) : !data ? (
        <Typography role="status">Cargando trazabilidad…</Typography>
      ) : (
        <Stack gap={2}>
          <Box>
            <Typography sx={{ fontWeight: 600 }} variant="body2">
              Notas de unidad
            </Typography>
            {data.unit_grades.length === 0 ? (
              <Typography color="text.secondary" variant="body2">
                Sin notas de unidad.
              </Typography>
            ) : (
              data.unit_grades.map((item) => (
                <Typography key={item.unit_number} variant="body2">
                  {item.unit_number}. {item.unit_name}: {item.value}
                </Typography>
              ))
            )}
          </Box>
          <Typography variant="body2">
            <strong>Recuperación:</strong>{" "}
            {data.recovery_grade ?? "Sin nota de recuperación"}
          </Typography>
          <Box>
            <Typography sx={{ fontWeight: 600 }} variant="body2">
              Correcciones
            </Typography>
            {data.corrections.length === 0 ? (
              <Typography color="text.secondary" variant="body2">
                Sin correcciones.
              </Typography>
            ) : (
              data.corrections.map((item, index) => (
                <Typography key={index} variant="body2">
                  {formatDateTime(item.corrected_at)} ·{" "}
                  {STAGE_LABEL[item.stage] ?? item.stage}
                  {item.unit_number
                    ? ` · unidad ${item.unit_number}`
                    : ""}: {item.previous_value ?? "—"} →{" "}
                  {item.new_value ?? "—"}
                  {item.reason ? ` · «${item.reason}»` : ""}
                  {item.corrected_by ? ` · ${item.corrected_by}` : ""}
                </Typography>
              ))
            )}
          </Box>
        </Stack>
      )}
    </FloatingWindow>
  );
}

/**
 * Resultados de un estudiante (docs/ux-ui.md V5): boleta por unidad y subárea,
 * nota final con su condición y, con el ciclo cerrado, los resultados
 * congelados, la promoción, la corrección con motivo y la trazabilidad.
 *
 * El estudiante se busca en el servidor y su matrícula del ciclo sale de su
 * historial: no se descarga ningún padrón (V7).
 */
export function ResultsTab({ cycle }) {
  const cycleId = cycle.public_id;
  const isClosed = cycle.status === "closed";
  const { can } = usePermissions();
  const canCorrect = can(PERMISSION.GRADE_CORRECT);
  const canTrace = can(PERMISSION.AUDIT_READ);
  const [params, setParams] = useUrlParams();
  const studentId = params.get("estudiante") ?? "";
  const [correcting, setCorrecting] = useState(null);
  const [tracing, setTracing] = useState(null);

  const history = useQuery({
    queryKey: queryKeys.evaluation(cycleId, "enrolment-of", studentId),
    queryFn: () =>
      enrolmentsService.listHistory({ student_id: studentId, page_size: 100 }),
    enabled: Boolean(studentId),
  });
  const enrolment = history.data
    ? enrolmentInCycle(history.data, cycleId)
    : null;
  const enrolmentId = enrolment?.public_id;

  const units = useCycleUnits(cycleId);
  const plan = usePlanSubjects(
    cycleId,
    enrolment?.grade?.public_id ?? enrolment?.grade_id
  );
  const card = useQuery({
    queryKey: queryKeys.evaluation(cycleId, "report-card", enrolmentId),
    queryFn: () => evaluationService.getReportCard(cycleId, enrolmentId),
    enabled: Boolean(enrolmentId),
  });
  const frozen = useQuery({
    queryKey: queryKeys.evaluation(cycleId, "frozen", enrolmentId),
    queryFn: () => evaluationService.listFrozenResults(cycleId, enrolmentId),
    enabled: Boolean(enrolmentId) && isClosed,
  });
  const promotion = useQuery({
    queryKey: queryKeys.evaluation(cycleId, "promotion", enrolmentId),
    queryFn: () => evaluationService.getFrozenPromotion(cycleId, enrolmentId),
    enabled: Boolean(enrolmentId) && isClosed,
    retry: false,
  });

  // Subáreas: las del plan del grado y, por si alguna salió del plan, las que
  // ya tienen nota. Los nombres vienen de las respuestas.
  const grades = Array.isArray(card.data)
    ? card.data
    : (card.data?.results ?? []);
  const subjects = new Map(
    (plan.data ?? []).map((item) => [item.value, item.label])
  );
  for (const grade of grades) {
    if (grade.subject_detail && !subjects.has(grade.subject_detail.public_id)) {
      subjects.set(grade.subject_detail.public_id, grade.subject_detail.name);
    }
  }
  const subjectRows = [...subjects].map(([id, name]) => ({ id, name }));

  // Con el ciclo abierto, la nota final se pide al backend por subárea: el
  // redondeo y la condición son suyos (RF-RES-001/002), no se recalculan aquí.
  const subjectIds = subjectRows.map((subject) => subject.id);
  const finals = useQuery({
    queryKey: queryKeys.evaluation(cycleId, "finals", enrolmentId, subjectIds),
    queryFn: async () => {
      const results = await Promise.all(
        subjectIds.map((subjectId) =>
          evaluationService.getFinalSubjectGrade(
            cycleId,
            enrolmentId,
            subjectId
          )
        )
      );
      return Object.fromEntries(subjectIds.map((id, i) => [id, results[i]]));
    },
    // Se espera a tener plan y boleta: la lista de subáreas ya no cambia.
    enabled:
      Boolean(enrolmentId) &&
      !isClosed &&
      plan.isSuccess &&
      card.isSuccess &&
      subjectIds.length > 0,
  });
  const frozenBySubject = new Map(
    (frozen.data ?? []).map((item) => [item.subject_id, item])
  );

  const unitList = units.data ?? [];
  const columns = [
    { key: "subject", label: "Subárea", render: (row) => row.name },
    ...unitList.map((unit) => ({
      key: `unit-${unit.public_id}`,
      label: unit.name,
      align: "right",
      render: (row) => {
        const grade = grades.find(
          (item) =>
            item.evaluation_unit_id === unit.public_id &&
            item.subject_detail?.public_id === row.id
        );
        return grade ? grade.value : <MutedCell>—</MutedCell>;
      },
    })),
    {
      key: "final",
      label: isClosed ? "Nota final (congelada)" : "Nota final",
      align: "right",
      render: (row) => {
        if (isClosed) {
          const result = frozenBySubject.get(row.id);
          return result?.final_grade ?? <MutedCell>Sin calificar</MutedCell>;
        }
        const data = finals.data?.[row.id];
        if (!data) return <MutedCell>…</MutedCell>;
        return (
          <Stack alignItems="flex-end">
            <span>{data.final_grade ?? "Sin calificar"}</span>
            <Typography color="text.secondary" variant="caption">
              {data.graded_units} de {data.total_units} unidades
            </Typography>
          </Stack>
        );
      },
    },
    {
      key: "condition",
      label: "Condición",
      render: (row) => {
        const result = isClosed
          ? frozenBySubject.get(row.id)
          : finals.data?.[row.id];
        return (
          <Stack gap={0.5}>
            <ConditionChip condition={result?.condition} />
            {result?.is_correction ? (
              <Typography color="text.secondary" variant="caption">
                Corregida: {result.correction_reason}
              </Typography>
            ) : null}
          </Stack>
        );
      },
    },
  ];

  const actionsFor = (row) => [
    {
      key: "correct",
      label: "Corregir",
      hidden: !isClosed || !canCorrect || !frozenBySubject.has(row.id),
      onClick: () =>
        setCorrecting({ ...row, result: frozenBySubject.get(row.id) }),
    },
    {
      key: "trace",
      label: "Ver trazabilidad",
      hidden: !canTrace,
      onClick: () => setTracing(row),
    },
  ];
  if (canTrace || (isClosed && canCorrect)) {
    columns.push({
      key: "acciones",
      label: "Acciones",
      align: "right",
      render: (row) => (
        <RowActionsMenu actions={actionsFor(row)} label={row.name} />
      ),
    });
  }

  const promotionData = promotion.data;

  return (
    <Stack gap={2}>
      <Box sx={{ maxWidth: 480 }}>
        <RemoteSearchSelect
          helperText="Busque por nombre, apellido o código."
          label="Estudiante"
          name="estudiante"
          onChange={(event) => setParams({ estudiante: event.target.value })}
          search={STUDENT_SEARCH}
          value={studentId}
        />
      </Box>

      {!studentId ? (
        <Typography color="text.secondary" variant="body2">
          Elija un estudiante para ver su boleta y sus resultados del ciclo.
        </Typography>
      ) : history.error ? (
        <Alert severity="error">{history.error.message}</Alert>
      ) : history.isPending ? (
        <Typography role="status">Buscando matrícula…</Typography>
      ) : !enrolment ? (
        <Alert severity="info">
          El estudiante no tiene matrícula en «{cycle.name}».
        </Alert>
      ) : (
        <SectionCard
          subtitle={[
            enrolment.student?.student_code,
            enrolment.section
              ? `${enrolment.section.grade_name ?? ""} ${enrolment.section.name}`.trim()
              : null,
            cycle.name,
          ]
            .filter(Boolean)
            .join(" · ")}
          title={`Boleta de ${enrolment.student?.full_name ?? "estudiante"}`}
        >
          <Stack gap={2} sx={{ p: { xs: 1.5, md: 2 } }}>
            {isClosed ? (
              promotionData ? (
                <Alert
                  severity={promotionData.promoted ? "success" : "warning"}
                >
                  {promotionData.promoted
                    ? "Promovido: aprobó todas las subáreas del ciclo."
                    : `No promovido: ${promotionData.failed_subjects.length} subáreas sin aprobar (${promotionData.failed_subjects.join(", ")}).`}
                  {promotionData.is_correction
                    ? ` Resultado corregido: ${promotionData.correction_reason}`
                    : ""}
                </Alert>
              ) : promotion.isError ? (
                <Alert severity="info">
                  No hay condición de promoción congelada para esta matrícula.
                </Alert>
              ) : null
            ) : (
              <Alert severity="info">
                El ciclo sigue abierto: la nota final se recalcula con cada nota
                registrada. Los resultados se congelan al cerrar el ciclo.
              </Alert>
            )}
            {card.error ? (
              <Alert severity="error">{card.error.message}</Alert>
            ) : null}
            {frozen.error ? (
              <Alert severity="error">{frozen.error.message}</Alert>
            ) : null}
            <SectionTableArea>
              <DataTable
                columns={columns}
                emptyMessage="El grado no tiene subáreas en el plan de estudios del ciclo."
                getRowKey={(row) => row.id}
                loading={card.isPending || plan.isPending}
                rows={subjectRows}
              />
            </SectionTableArea>
          </Stack>
        </SectionCard>
      )}

      {correcting ? (
        <EntityFormWindow
          description={`Corrige la nota final congelada de ${correcting.name}. No se reescribe el resultado anterior: queda una nueva versión con el motivo, auditada.`}
          fields={[
            {
              name: "final_grade",
              label: "Nota final corregida (0–100)",
              type: "number",
              min: 0,
              max: 100,
              required: true,
            },
            {
              name: "reason",
              label: "Motivo de la corrección",
              type: "textarea",
              required: true,
            },
          ]}
          initialValues={{
            final_grade: correcting.result?.final_grade ?? "",
            reason: "",
          }}
          onCancel={() => setCorrecting(null)}
          onSubmit={async (values) => {
            await evaluationService.correctFrozenResult(
              cycleId,
              enrolmentId,
              correcting.id,
              values
            );
            setCorrecting(null);
          }}
          open
          submitLabel="Corregir resultado"
          title="Corregir resultado congelado"
        />
      ) : null}

      {tracing ? (
        <TraceWindow
          enrolmentId={enrolmentId}
          onClose={() => setTracing(null)}
          subject={tracing}
        />
      ) : null}
    </Stack>
  );
}
