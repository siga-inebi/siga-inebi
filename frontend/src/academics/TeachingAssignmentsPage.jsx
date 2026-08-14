import { useCallback, useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import SwapHorizOutlinedIcon from "@mui/icons-material/SwapHorizOutlined";

import { academicsService, PAGE_SIZE } from "@academics/academicsService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDate } from "@shared/utils/format.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { CodeCell, MutedCell } from "@ui/table/cells.jsx";

const ASSIGNMENT_FIELDS = [
  { name: "academic_cycle_id", label: "ID de ciclo escolar", required: true },
  { name: "section_id", label: "ID de seccion", required: true },
  { name: "subject_id", label: "ID de curso", required: true },
  { name: "teacher_id", label: "ID de docente", required: true },
  { name: "starts_on", label: "Vigente desde", type: "date", required: true, span: "full" },
];

const REASSIGN_FIELDS = [
  { name: "teacher_id", label: "ID del docente entrante", required: true },
  {
    name: "ends_on",
    label: "Ultimo dia del docente saliente",
    type: "date",
    required: true,
    help: "La asignacion anterior se cierra en esta fecha y la nueva arranca al dia siguiente.",
  },
];

/**
 * Asignaciones docentes por seccion y curso.
 *
 * El listado es el HISTORIAL (`/teaching-assignments/history/`): el backend no
 * publica un listado de asignaciones vigentes, y con razon — una asignacion
 * cerrada sigue siendo la respuesta correcta a "quien daba este curso en marzo".
 * La columna de vigencia es la que distingue una cosa de la otra.
 *
 * Reasignar NO edita: cierra la asignacion actual y crea una nueva. Por eso la
 * accion pide la fecha de corte en vez de un docente a secas.
 */
export function TeachingAssignmentsPage() {
  const [cycleFilter, setCycleFilter] = useState("");
  const [creating, setCreating] = useState(false);
  const [reassigning, setReassigning] = useState(null);
  const [actionError, setActionError] = useState("");

  const loadHistory = useCallback(
    (params) =>
      academicsService.listTeachingAssignmentHistory({
        ...params,
        academic_cycle_id: cycleFilter.trim() || undefined,
      }),
    [cycleFilter]
  );
  const list = usePaginatedList(loadHistory, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  const handleCreate = async (payload) => {
    await academicsService.createTeachingAssignment(payload);
    setCreating(false);
    list.refresh();
  };

  const handleReassign = async (payload) => {
    setActionError("");
    try {
      await academicsService.reassignTeachingAssignment(reassigning.public_id, payload);
      setReassigning(null);
      list.refresh();
    } catch (requestError) {
      setActionError(requestError.message);
      throw requestError;
    }
  };

  const columns = [
    {
      key: "section_id",
      label: "Seccion",
      render: (row) => <CodeCell value={row.section_id} />,
    },
    { key: "subject_id", label: "Curso", render: (row) => <CodeCell value={row.subject_id} /> },
    { key: "teacher_id", label: "Docente", render: (row) => <CodeCell value={row.teacher_id} /> },
    {
      key: "academic_cycle_id",
      label: "Ciclo",
      render: (row) => <CodeCell value={row.academic_cycle_id} />,
    },
    {
      key: "starts_on",
      label: "Desde",
      render: (row) => (row.starts_on ? formatDate(row.starts_on) : <MutedCell>Sin fecha</MutedCell>),
    },
    {
      key: "ends_on",
      label: "Vigencia",
      render: (row) =>
        row.ends_on ? (
          <Stack gap={0.25}>
            <StatusChip label="Cerrada" variant="neutral" />
            <MutedCell>hasta {formatDate(row.ends_on)}</MutedCell>
          </Stack>
        ) : (
          <StatusChip label="Vigente" variant="success" />
        ),
    },
  ];

  return (
    <>
      <PageHeader
        action={
          <Button
            onClick={() => setCreating(true)}
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nueva asignacion
          </Button>
        }
        breadcrumb="Estructura academica"
        subtitle="Historial de asignaciones docentes por seccion y curso. Reasignar cierra la asignacion vigente y abre una nueva; nada se sobrescribe."
        title="Asignaciones docentes"
      />

      <ListSection
        actionError={actionError}
        columns={[
          ...columns,
          {
            key: "acciones",
            label: "Acciones",
            align: "right",
            render: (row) =>
              row.ends_on ? null : (
                <ActionIconButton
                  label="Reasignar a otro docente"
                  onClick={() => setReassigning(row)}
                >
                  <SwapHorizOutlinedIcon fontSize="small" />
                </ActionIconButton>
              ),
          },
        ]}
        emptyMessage={
          cycleFilter
            ? "Sin asignaciones para ese ciclo."
            : "Todavia no hay asignaciones docentes registradas."
        }
        fillHeight
        filters={
          <FilterBar onClear={cycleFilter ? () => setCycleFilter("") : undefined}>
            <SearchField
              onChange={setCycleFilter}
              placeholder="Filtrar por ID de ciclo escolar…"
              value={cycleFilter}
            />
          </FilterBar>
        }
        getRowKey={(row) => row.public_id}
        list={list}
        showInactiveToggle={false}
        subtitle="Vigentes y cerradas"
        title="Historial de asignaciones"
      />

      <EntityFormWindow
        description="La asignacion vincula un docente con una seccion y un curso dentro de un ciclo."
        fields={ASSIGNMENT_FIELDS}
        initialValues={{
          academic_cycle_id: "",
          section_id: "",
          subject_id: "",
          teacher_id: "",
          starts_on: "",
        }}
        key={creating ? "assignment-create-open" : "assignment-create-closed"}
        onCancel={() => setCreating(false)}
        onSubmit={handleCreate}
        open={creating}
        submitLabel="Crear asignacion"
        title="Nueva asignacion docente"
      />

      {reassigning ? (
        <EntityFormWindow
          description="La asignacion actual se cierra en la fecha indicada y el docente entrante toma el curso desde ese corte."
          fields={REASSIGN_FIELDS}
          initialValues={{ teacher_id: "", ends_on: "" }}
          key={`reassign-${reassigning.public_id}`}
          onCancel={() => setReassigning(null)}
          onSubmit={handleReassign}
          open
          submitLabel="Reasignar"
          title="Reasignar curso"
        />
      ) : null}
    </>
  );
}
