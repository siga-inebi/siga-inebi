import { useState } from "react";

import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";

import { formatDate } from "@shared/utils/format.js";
import { DetailField } from "@ui/layout/DetailWindow.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";

const HISTORY_TABS = [
  ["offerings", "Oferta de grados"],
  ["plans", "Plan de estudios"],
  ["assignments", "Asignaciones docentes"],
];
const ROWS_PER_PAGE = 10;

function refLabel(value) {
  if (value == null) return "—";
  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }
  return value.name ?? value.code ?? "—";
}

function HistoryTable({ columns, emptyMessage, rows }) {
  const [page, setPage] = useState(0);
  const totalPages = Math.max(1, Math.ceil(rows.length / ROWS_PER_PAGE));
  const currentPage = Math.min(page, totalPages - 1);
  const visibleRows = rows.slice(
    currentPage * ROWS_PER_PAGE,
    (currentPage + 1) * ROWS_PER_PAGE
  );

  return (
    <DataTable
      columns={columns}
      emptyMessage={emptyMessage}
      getRowKey={(row, index) => row.public_id ?? `${currentPage}-${index}`}
      pagination={
        rows.length > ROWS_PER_PAGE
          ? {
              page: currentPage,
              rowsPerPage: ROWS_PER_PAGE,
              total: rows.length,
              onPageChange: setPage,
            }
          : undefined
      }
      rows={visibleRows}
    />
  );
}

/**
 * Estructura registrada del ciclo, solo consulta. Cada colección tiene su
 * propia pestaña y tabla paginada: no combina listas largas con scroll interno.
 */
export function CycleHistory({ detail }) {
  const [tab, setTab] = useState("offerings");
  const offerings = detail?.grade_offerings ?? [];
  const plans = detail?.curriculum_plans ?? [];
  const assignments = detail?.teaching_assignments ?? [];
  const enrolments = detail?.enrolments;
  const countByTab = {
    offerings: offerings.length,
    plans: plans.length,
    assignments: assignments.length,
  };

  return (
    <Box>
      {enrolments ? (
        <Box
          component="dl"
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr 1fr", sm: "repeat(4, 1fr)" },
            gap: 2,
            mb: 3,
            mt: 0,
          }}
        >
          <DetailField label="Matrículas" value={enrolments.total} />
          <DetailField label="Activas" value={enrolments.active} />
          <DetailField label="Retiradas" value={enrolments.withdrawn} />
          <DetailField label="Finalizadas" value={enrolments.completed} />
        </Box>
      ) : null}

      <Tabs
        allowScrollButtonsMobile
        aria-label="Estructura registrada"
        onChange={(_event, next) => setTab(next)}
        scrollButtons="auto"
        value={tab}
        variant="scrollable"
      >
        {HISTORY_TABS.map(([id, label]) => (
          <Tab
            aria-controls={`history-panel-${id}`}
            id={`history-tab-${id}`}
            key={id}
            label={`${label} (${countByTab[id]})`}
            value={id}
          />
        ))}
      </Tabs>

      <Box
        aria-labelledby={`history-tab-${tab}`}
        id={`history-panel-${tab}`}
        role="tabpanel"
        sx={{ pt: 2 }}
      >
        {tab === "offerings" ? (
          <HistoryTable
            columns={[
              {
                key: "grade",
                label: "Grado",
                render: (row) => refLabel(row.grade),
              },
              {
                key: "shift",
                label: "Jornada",
                render: (row) => refLabel(row.shift),
              },
              {
                key: "campus",
                label: "Sede",
                render: (row) => refLabel(row.campus),
              },
              {
                key: "sections",
                label: "Secciones",
                align: "right",
                render: (row) => row.sections?.length ?? 0,
              },
            ]}
            emptyMessage="Este ciclo no registró oferta de grados."
            rows={offerings}
          />
        ) : null}
        {tab === "plans" ? (
          <HistoryTable
            columns={[
              {
                key: "grade",
                label: "Grado",
                render: (row) => refLabel(row.grade),
              },
              {
                key: "subject",
                label: "Curso",
                render: (row) => refLabel(row.subject),
              },
              {
                key: "required",
                label: "Tipo",
                render: (row) => (row.is_required ? "Obligatorio" : "Opcional"),
              },
            ]}
            emptyMessage="Este ciclo no registró plan de estudios."
            rows={plans}
          />
        ) : null}
        {tab === "assignments" ? (
          <HistoryTable
            columns={[
              {
                key: "section",
                label: "Sección",
                render: (row) =>
                  [row.section?.grade_name, row.section?.name]
                    .filter(Boolean)
                    .join(" ") || "Sección sin nombre",
              },
              {
                key: "subject",
                label: "Curso",
                render: (row) => row.subject?.name ?? "Curso sin nombre",
              },
              {
                key: "teacher",
                label: "Docente",
                render: (row) => row.teacher?.name ?? "Docente sin nombre",
              },
              {
                key: "starts_on",
                label: "Desde",
                render: (row) => formatDate(row.starts_on),
              },
            ]}
            emptyMessage="Este ciclo no registró asignaciones docentes."
            rows={assignments}
          />
        ) : null}
      </Box>
    </Box>
  );
}
