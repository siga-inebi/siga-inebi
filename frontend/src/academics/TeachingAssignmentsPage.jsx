import { useCallback, useMemo, useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import PlaylistAddCheckOutlinedIcon from "@mui/icons-material/PlaylistAddCheckOutlined";
import SwapHorizOutlinedIcon from "@mui/icons-material/SwapHorizOutlined";

import { academicsService, PAGE_SIZE } from "@academics/academicsService.js";
import {
  labelIndex,
  sectionsForCycle,
  useCycleCatalog,
  useSectionCatalog,
  useSubjectCatalog,
  useTeacherCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDate } from "@shared/utils/format.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { CodeCell, MutedCell } from "@ui/table/cells.jsx";

import { BulkAssignmentWindow } from "./BulkAssignmentWindow.jsx";

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
 *
 * El backend habla en UUIDs (`section_id`, `subject_id`, `teacher_id`) tanto al
 * listar como al crear. La pantalla los traduce en ambas direcciones contra los
 * catalogos: se eligen nombres, se muestran nombres, y el UUID no aparece nunca
 * a la vista de quien usa el sistema.
 */
export function TeachingAssignmentsPage() {
  const [cycleFilter, setCycleFilter] = useState("");
  const [creating, setCreating] = useState(false);
  const [bulkAssigning, setBulkAssigning] = useState(false);
  const [reassigning, setReassigning] = useState(null);
  const [actionError, setActionError] = useState("");

  const cycles = useCycleCatalog();
  const sections = useSectionCatalog();
  const subjects = useSubjectCatalog();
  const teachers = useTeacherCatalog();

  const loadHistory = useCallback(
    (params) =>
      academicsService.listTeachingAssignmentHistory({
        ...params,
        academic_cycle_id: cycleFilter || undefined,
      }),
    [cycleFilter]
  );
  const list = usePaginatedList(loadHistory, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  const names = useMemo(
    () => ({
      cycles: labelIndex(cycles.options),
      sections: labelIndex(sections.options),
      subjects: labelIndex(subjects.options),
      teachers: labelIndex(teachers.options),
    }),
    [cycles.options, sections.options, subjects.options, teachers.options]
  );

  const assignmentFields = useCallback(
    (values) => [
      {
        name: "academic_cycle_id",
        label: "Ciclo escolar",
        type: "select",
        options: cycles.options,
        loading: cycles.loading,
        optionsError: cycles.error,
        emptyHint: "No hay ciclos escolares registrados.",
        required: true,
        // Cambiar de ciclo invalida la seccion elegida: pertenece al ciclo
        // anterior y el backend la rechazaria al guardar.
        resets: ["section_id"],
      },
      {
        name: "section_id",
        label: "Seccion",
        type: "select",
        options: sectionsForCycle(sections.options, values.academic_cycle_id),
        loading: sections.loading,
        optionsError: sections.error,
        emptyHint: values.academic_cycle_id
          ? "Ese ciclo no tiene secciones registradas."
          : "Elija primero el ciclo escolar.",
        required: true,
      },
      {
        name: "subject_id",
        label: "Curso",
        type: "select",
        options: subjects.options,
        loading: subjects.loading,
        optionsError: subjects.error,
        emptyHint: "No hay cursos registrados.",
        required: true,
      },
      {
        name: "teacher_id",
        label: "Docente",
        type: "select",
        options: teachers.options,
        loading: teachers.loading,
        optionsError: teachers.error,
        emptyHint: "No hay docentes registrados.",
        required: true,
      },
      {
        name: "starts_on",
        label: "Vigente desde",
        type: "date",
        required: true,
        span: "full",
      },
    ],
    [cycles, sections, subjects, teachers]
  );

  const reassignFields = useMemo(
    () => [
      {
        name: "teacher_id",
        label: "Docente entrante",
        type: "select",
        options: teachers.options,
        loading: teachers.loading,
        optionsError: teachers.error,
        emptyHint: "No hay docentes registrados.",
        required: true,
      },
      {
        name: "ends_on",
        label: "Ultimo dia del docente saliente",
        type: "date",
        required: true,
        help: "La asignacion anterior se cierra en esta fecha y la nueva arranca al dia siguiente.",
      },
    ],
    [teachers]
  );

  const handleCreate = async (payload) => {
    await academicsService.createTeachingAssignment(payload);
    setCreating(false);
    list.refresh();
  };

  const handleReassign = async (payload) => {
    setActionError("");
    try {
      await academicsService.reassignTeachingAssignment(
        reassigning.public_id,
        payload
      );
      setReassigning(null);
      list.refresh();
    } catch (requestError) {
      setActionError(requestError.message);
      throw requestError;
    }
  };

  /**
   * Nombre del catalogo, o el identificador crudo si todavia no llego.
   *
   * El respaldo importa: un catalogo que aun carga (o un registro dado de baja
   * que ya no figura en el) dejaria la celda vacia, y una fila sin datos se lee
   * como un error del sistema.
   */
  const nameCell = (index, id) =>
    index.get(id) ?? (id ? <CodeCell value={id} /> : <MutedCell>—</MutedCell>);

  const columns = [
    {
      key: "section_id",
      label: "Seccion",
      render: (row) => nameCell(names.sections, row.section_id),
    },
    {
      key: "subject_id",
      label: "Curso",
      render: (row) => nameCell(names.subjects, row.subject_id),
    },
    {
      key: "teacher_id",
      label: "Docente",
      render: (row) => nameCell(names.teachers, row.teacher_id),
    },
    {
      key: "academic_cycle_id",
      label: "Ciclo",
      render: (row) => nameCell(names.cycles, row.academic_cycle_id),
    },
    {
      key: "starts_on",
      label: "Desde",
      render: (row) =>
        row.starts_on ? (
          formatDate(row.starts_on)
        ) : (
          <MutedCell>Sin fecha</MutedCell>
        ),
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
          <Stack direction="row" flexWrap="wrap" gap={1}>
            <Button
              onClick={() => setBulkAssigning(true)}
              startIcon={<PlaylistAddCheckOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              Asignar por lotes
            </Button>
            <Button
              onClick={() => setCreating(true)}
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Nueva asignacion
            </Button>
          </Stack>
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
          <FilterBar
            onClear={cycleFilter ? () => setCycleFilter("") : undefined}
          >
            <FilterSelect
              emptyLabel="Todos los ciclos"
              label="Ciclo escolar"
              loading={cycles.loading}
              minWidth={220}
              onChange={setCycleFilter}
              options={cycles.options}
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
        fields={assignmentFields}
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

      {bulkAssigning ? (
        <BulkAssignmentWindow
          onClose={() => setBulkAssigning(false)}
          onCreated={list.refresh}
        />
      ) : null}

      {reassigning ? (
        <EntityFormWindow
          description="La asignacion actual se cierra en la fecha indicada y el docente entrante toma el curso desde ese corte."
          fields={reassignFields}
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
