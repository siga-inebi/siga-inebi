import { useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { academicsService } from "@academics/academicsService.js";
import { TEACHER_SEARCH } from "@academics/searchOptions.js";
import { cyclesService } from "@cycles/cyclesService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { formatDate, todayInputValue } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";

import { useGradeOptions } from "../structureOptions.js";

function sectionName(section) {
  return [section.grade?.name, section.name].filter(Boolean).join(" ");
}

function Cell({ cell, onAssign, onReplace, section }) {
  const subject = cell.subject?.name ?? "Curso";
  if (!cell.assignment) {
    return onAssign ? (
      <Button
        aria-label={`Asignar ${subject} en ${sectionName(section)}`}
        color="warning"
        onClick={() => onAssign(section, cell)}
        size="small"
        sx={{ justifyContent: "flex-start" }}
        variant="outlined"
      >
        {subject}: Asignar
      </Button>
    ) : (
      <StatusChip label={`${subject}: sin docente`} variant="warning" />
    );
  }
  const teacher = cell.assignment.teacher?.name ?? "Docente";
  const text = `${subject}: ${teacher}`;
  return onReplace ? (
    <Button
      aria-label={`Reemplazar docente de ${subject} en ${sectionName(section)}`}
      onClick={() => onReplace(section, cell)}
      size="small"
      sx={{ justifyContent: "flex-start", textTransform: "none" }}
      title={`Desde ${formatDate(cell.assignment.starts_on)}`}
      variant="text"
    >
      {text}
    </Button>
  ) : (
    <Typography sx={{ fontSize: "0.8125rem", px: 1, py: 0.5 }}>
      {text}
    </Typography>
  );
}

/**
 * Matriz sección × curso del ciclo (docs/ux-ui.md AD1, AD3): de un vistazo,
 * qué curso de qué sección no tiene docente — justo lo que bloquea la
 * activación — y asignarlo con un clic. Una celda llena permite reemplazar al
 * docente (reasignación con fecha de cierre; el historial se conserva).
 */
export function AssignmentMatrixTab({ canManage, cycle }) {
  const cycleId = cycle.public_id;
  const canWrite = canManage && cycle.status !== "closed";
  const grades = useGradeOptions();
  const [assigning, setAssigning] = useState(null);
  const [replacing, setReplacing] = useState(null);

  const list = useServerList({
    queryKey: queryKeys.academics.matrix(cycleId),
    fetchPage: (params) => cyclesService.assignmentMatrix(cycleId, params),
    defaultFilters: { grade_id: "" },
    urlPrefix: "mat_",
    enabled: canManage,
  });

  if (!canManage) {
    return (
      <Alert severity="info">
        La matriz de asignaciones requiere el permiso para administrar catálogos
        institucionales.
      </Alert>
    );
  }

  const missing = list.items.reduce(
    (total, row) => total + row.cells.filter((cell) => !cell.assignment).length,
    0
  );

  const columns = [
    {
      key: "section",
      label: "Sección",
      render: (row) => (
        <Stack>
          <Typography sx={{ fontWeight: 600, fontSize: "0.875rem" }}>
            {sectionName(row.section)}
          </Typography>
          <Typography color="text.secondary" sx={{ fontSize: "0.75rem" }}>
            {row.section.shift?.name}
          </Typography>
        </Stack>
      ),
    },
    {
      key: "cells",
      label: "Cursos del plan y docente",
      render: (row) =>
        row.cells.length === 0 ? (
          <Typography color="text.secondary" variant="body2">
            El grado no tiene cursos en el plan de estudios del ciclo.
          </Typography>
        ) : (
          <Box
            sx={{
              display: "grid",
              gap: 0.75,
              gridTemplateColumns: {
                xs: "1fr",
                md: "repeat(2, minmax(0, 1fr))",
                lg: "repeat(3, minmax(0, 1fr))",
              },
            }}
          >
            {row.cells.map((cell) => (
              <Cell
                cell={cell}
                key={cell.subject.public_id}
                onAssign={canWrite ? setAssigningFor : undefined}
                onReplace={canWrite ? setReplacingFor : undefined}
                section={row.section}
              />
            ))}
          </Box>
        ),
    },
    {
      key: "missing",
      label: "Faltan",
      align: "right",
      render: (row) => {
        const count = row.cells.filter((cell) => !cell.assignment).length;
        return count ? (
          <StatusChip label={String(count)} variant="warning" />
        ) : (
          <StatusChip label="Completa" variant="success" />
        );
      },
    },
  ];

  function setAssigningFor(section, cell) {
    setAssigning({ section, cell });
  }
  function setReplacingFor(section, cell) {
    setReplacing({ section, cell });
  }

  return (
    <>
      {missing > 0 ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          En esta página faltan {missing}{" "}
          {missing === 1 ? "docente" : "docentes"}. Cada curso del plan sin
          docente impide activar el ciclo.
        </Alert>
      ) : null}
      <ListSection
        columns={columns}
        emptyMessage={
          list.filters.grade_id
            ? "El grado elegido no tiene secciones activas en este ciclo."
            : "Este ciclo no tiene secciones activas."
        }
        filters={
          <FilterBar
            onClear={
              list.filters.grade_id
                ? () => list.setFilter("grade_id", "")
                : undefined
            }
          >
            <FilterSelect
              emptyLabel="Todos los grados"
              label="Grado"
              loading={grades.loading}
              onChange={(value) => list.setFilter("grade_id", value)}
              options={grades.options}
              value={list.filters.grade_id}
            />
          </FilterBar>
        }
        getRowKey={(row) => row.section.public_id}
        list={list}
        showInactiveToggle={false}
        subtitle="Una fila por sección; las columnas son los cursos del plan de su grado."
        title="Asignaciones del ciclo"
      />

      {assigning ? (
        <EntityFormWindow
          description={`${assigning.cell.subject.name} en ${sectionName(assigning.section)}.`}
          fields={[
            {
              name: "teacher_id",
              label: "Docente",
              type: "search-select",
              required: true,
              span: "full",
              search: TEACHER_SEARCH,
            },
          ]}
          initialValues={{ teacher_id: "" }}
          onCancel={() => setAssigning(null)}
          onSubmit={async ({ teacher_id }) => {
            const result = await cyclesService.createAssignmentsBatch(cycleId, {
              items: [
                {
                  section_id: assigning.section.public_id,
                  subject_id: assigning.cell.subject.public_id,
                  teacher_id,
                },
              ],
            });
            if (result?.failed?.length) {
              throw new Error(result.failed[0].detail);
            }
            setAssigning(null);
            list.refresh();
          }}
          open
          submitLabel="Asignar"
          title="Asignar docente"
        />
      ) : null}

      {replacing ? (
        <EntityFormWindow
          description={`${replacing.cell.subject.name} en ${sectionName(replacing.section)}, hoy a cargo de ${replacing.cell.assignment.teacher?.name}. La asignación actual termina en la fecha indicada y la nueva empieza al día siguiente.`}
          fields={[
            {
              name: "teacher_id",
              label: "Nuevo docente",
              type: "search-select",
              required: true,
              search: TEACHER_SEARCH,
            },
            {
              name: "ends_on",
              label: "Fin de la asignación actual",
              type: "date",
              required: true,
            },
          ]}
          initialValues={{ teacher_id: "", ends_on: todayInputValue() }}
          onCancel={() => setReplacing(null)}
          onSubmit={async (values) => {
            await academicsService.reassignTeachingAssignment(
              replacing.cell.assignment.public_id,
              values
            );
            setReplacing(null);
            list.refresh();
          }}
          open
          submitLabel="Reemplazar"
          title="Reemplazar docente"
        />
      ) : null}
    </>
  );
}
