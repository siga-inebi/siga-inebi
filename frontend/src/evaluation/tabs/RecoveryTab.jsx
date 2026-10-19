import { useState } from "react";

import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { evaluationService } from "@evaluation/evaluationService.js";
import {
  sectionOptions,
  useCycleSections,
  useUrlParams,
} from "@evaluation/evaluationData.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { formatPercent } from "@shared/utils/format.js";
import { RowActionsMenu } from "@ui/buttons/RowActionsMenu.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";

const COLUMNS = [
  {
    key: "student",
    label: "Estudiante",
    render: (row) => (
      <Stack>
        <span>{row.student?.full_name}</span>
        <Typography color="text.secondary" variant="caption">
          {row.student?.student_code}
        </Typography>
      </Stack>
    ),
  },
  {
    key: "attendance",
    label: "Asistencia",
    align: "right",
    render: (row) => formatPercent(row.attendance_percentage),
  },
  {
    key: "failed",
    label: "Reprobadas",
    align: "right",
    render: (row) => `${row.failed_count} de ${row.failed_limit} permitidas`,
  },
  {
    key: "subjects",
    label: "Subáreas reprobadas",
    render: (row) =>
      row.failed_subjects.length === 0
        ? "Ninguna"
        : row.failed_subjects
            .map((subject) =>
              subject.final_grade == null
                ? subject.name
                : `${subject.name} (${subject.final_grade})`
            )
            .join(", "),
  },
  {
    key: "eligible",
    label: "Recuperación",
    render: (row) => (
      <Stack gap={0.5}>
        <StatusChip
          label={row.eligible ? "Elegible" : "No elegible"}
          variant={row.eligible ? "success" : "neutral"}
        />
        {row.eligible || row.reasons.length === 0 ? null : (
          <Typography color="text.secondary" variant="caption">
            {row.reasons.join(" ")}
          </Typography>
        )}
      </Stack>
    ),
  },
];

/**
 * Recuperación de una sección (RF-RES-004/005, docs/ux-ui.md V4): quién puede
 * ir a recuperación, por qué no los demás, y el registro de la nota de cada
 * subárea reprobada. Las reglas viven en el backend; aquí solo se muestran.
 */
export function RecoveryTab({ cycle }) {
  const cycleId = cycle.public_id;
  const { can } = usePermissions();
  const canWrite = can(PERMISSION.GRADE_WRITE);
  const [params, setParams] = useUrlParams();
  const sectionId = params.get("seccion") ?? "";
  const sections = useCycleSections(cycleId);
  const [registering, setRegistering] = useState(null);

  const list = useServerList({
    queryKey: queryKeys.evaluation(cycleId, "recovery", sectionId),
    fetchPage: (query) =>
      evaluationService.listSectionRecovery(cycleId, sectionId, query),
    enabled: Boolean(sectionId),
    urlPrefix: "rec_",
  });

  return (
    <>
      <ListSection
        columns={COLUMNS}
        emptyMessage={
          sectionId
            ? "La sección no tiene matrículas activas."
            : "Elija una sección para ver quién puede ir a recuperación."
        }
        filters={
          <FilterBar>
            <FilterSelect
              emptyLabel="Elija una sección"
              label="Sección"
              loading={sections.isPending}
              minWidth={240}
              onChange={(value) => setParams({ seccion: value, rec_page: "" })}
              options={sectionOptions(sections.data)}
              value={sectionId}
            />
          </FilterBar>
        }
        getRowKey={(row) => row.enrolment_id}
        list={list}
        renderActions={
          canWrite
            ? (row) => (
                <RowActionsMenu
                  actions={row.failed_subjects.map((subject) => ({
                    key: subject.public_id,
                    label: `Registrar recuperación de ${subject.name}`,
                    hidden: !row.eligible,
                    onClick: () => setRegistering({ row, subject }),
                  }))}
                  label={row.student?.full_name ?? "estudiante"}
                />
              )
            : undefined
        }
        showInactiveToggle={false}
        subtitle="Elegibilidad por asistencia, número de subáreas reprobadas y recuperación ya usada."
        title="Recuperación"
      />

      {registering ? (
        <EntityFormWindow
          description={`Nota de recuperación de ${registering.row.student?.full_name} en ${registering.subject.name}. Se registra dentro de la ventana de recuperación del ciclo y decide la condición de la subárea.`}
          fields={[
            {
              name: "value",
              label: "Nota de recuperación (0–100)",
              type: "number",
              min: 0,
              max: 100,
              required: true,
            },
          ]}
          initialValues={{ value: "" }}
          onCancel={() => setRegistering(null)}
          onSubmit={async ({ value }) => {
            await evaluationService.registerRecoveryGrade(
              cycleId,
              registering.row.enrolment_id,
              { subject: registering.subject.public_id, value }
            );
            setRegistering(null);
            list.refresh();
          }}
          open
          submitLabel="Registrar recuperación"
          title="Registrar recuperación"
        />
      ) : null}
    </>
  );
}
