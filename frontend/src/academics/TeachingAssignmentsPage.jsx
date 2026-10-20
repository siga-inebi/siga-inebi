import { lazy, Suspense, useCallback, useMemo, useState } from "react";

import Button from "@mui/material/Button";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import AddIcon from "@mui/icons-material/Add";
import ContentCopyOutlinedIcon from "@mui/icons-material/ContentCopyOutlined";
import PlaylistAddCheckOutlinedIcon from "@mui/icons-material/PlaylistAddCheckOutlined";
import SwapHorizOutlinedIcon from "@mui/icons-material/SwapHorizOutlined";

import { academicsService } from "@academics/academicsService.js";
import {
  SUBJECT_SEARCH,
  TEACHER_SEARCH,
  sectionLabel,
  sectionSearch,
} from "@academics/searchOptions.js";
import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import {
  labelIndex,
  useCycleCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { formatDate } from "@shared/utils/format.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

// Las ventanas de carga masiva y el buscador remoto se descargan al usarlos.
const BulkAssignmentWindow = lazy(() =>
  import("./BulkAssignmentWindow.jsx").then((module) => ({
    default: module.BulkAssignmentWindow,
  }))
);
const CloneAssignmentsWindow = lazy(() =>
  import("./CloneAssignmentsWindow.jsx").then((module) => ({
    default: module.CloneAssignmentsWindow,
  }))
);
const RemoteSearchSelect = lazy(() =>
  import("@ui/forms/RemoteSearchSelect.jsx").then((module) => ({
    default: module.RemoteSearchSelect,
  }))
);

const FILTERS = {
  academic_cycle_id: "",
  section_id: "",
  teacher_id: "",
  current: "",
};

function subjectName(subject) {
  if (!subject) return "Curso sin nombre";
  return subject.code ? `${subject.name} (${subject.code})` : subject.name;
}

/**
 * Asignaciones docentes por sección y curso (docs/ux-ui.md 2.5, AD2).
 *
 * El listado sale de `GET /academics/teaching-assignments/`, paginado y
 * filtrado en el servidor (ciclo, sección, docente y vigencia en la URL), y
 * trae los nombres de sección, curso y docente: la pantalla ya no descarga
 * catálogos para traducir identificadores.
 *
 * Reasignar NO edita: cierra la asignación vigente y abre otra. Por eso la
 * acción pide la fecha de corte.
 *
 * Tres formas de dar de alta, según cuánto se repite lo que se captura: una a
 * una, una sección completa por lotes o el ciclo anterior completo para
 * confirmar.
 */
export function TeachingAssignmentsPage() {
  const { can } = usePermissions();
  const canManage = can(PERMISSION.SCOPE_ASSIGN);

  const [creating, setCreating] = useState(false);
  const [bulkAssigning, setBulkAssigning] = useState(false);
  const [cloning, setCloning] = useState(false);
  const [reassigning, setReassigning] = useState(null);
  const [actionError, setActionError] = useState("");

  // Los ciclos son pocos (uno por año): el filtro los lista completos.
  const cycles = useCycleCatalog();
  const cycleNames = useMemo(
    () => labelIndex(cycles.options),
    [cycles.options]
  );

  const list = useServerList({
    queryKey: queryKeys.academics.list("teaching-assignments"),
    fetchPage: academicsService.listTeachingAssignments,
    defaultFilters: FILTERS,
  });
  const { filters } = list;

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
        // Cambiar de ciclo invalida la sección elegida: pertenece al otro
        // ciclo y el backend la rechazaría al guardar.
        resets: ["section_id"],
      },
      values.academic_cycle_id
        ? {
            name: "section_id",
            label: "Sección",
            type: "search-select",
            required: true,
            search: sectionSearch(values.academic_cycle_id),
            placeholder: "Escriba el grado o la sección",
          }
        : {
            name: "section_id",
            label: "Sección",
            type: "select",
            options: [],
            emptyHint: "Elija primero el ciclo escolar.",
            required: true,
          },
      {
        name: "subject_id",
        label: "Curso",
        type: "search-select",
        required: true,
        search: SUBJECT_SEARCH,
        help: "Debe estar en el plan de estudios del grado de la sección.",
      },
      {
        name: "teacher_id",
        label: "Docente",
        type: "search-select",
        required: true,
        search: TEACHER_SEARCH,
      },
      {
        name: "starts_on",
        label: "Vigente desde",
        type: "date",
        required: true,
        span: "full",
      },
    ],
    [cycles]
  );

  const reassignFields = [
    {
      name: "teacher_id",
      label: "Docente entrante",
      type: "search-select",
      required: true,
      search: TEACHER_SEARCH,
    },
    {
      name: "ends_on",
      label: "Último día del docente saliente",
      type: "date",
      required: true,
      help: "La asignación anterior se cierra en esta fecha y la nueva empieza al día siguiente.",
    },
  ];

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

  const columns = [
    {
      key: "section",
      label: "Sección",
      render: (row) =>
        row.section ? (
          sectionLabel(row.section)
        ) : (
          <MutedCell>Sección sin nombre</MutedCell>
        ),
    },
    {
      key: "subject",
      label: "Curso",
      render: (row) => subjectName(row.subject),
    },
    {
      key: "teacher",
      label: "Docente",
      render: (row) =>
        row.teacher?.name || <MutedCell>Docente sin nombre</MutedCell>,
    },
    {
      key: "academic_cycle_id",
      label: "Ciclo",
      render: (row) =>
        cycleNames.get(row.academic_cycle_id) ?? <MutedCell>—</MutedCell>,
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
            <StatusChip label="Finalizada" variant="neutral" />
            <MutedCell>hasta {formatDate(row.ends_on)}</MutedCell>
          </Stack>
        ) : (
          <StatusChip label="Vigente" variant="success" />
        ),
    },
  ];

  const hasFilters = Object.values(filters).some(Boolean);

  return (
    <>
      <PageHeader
        action={
          canManage ? (
            <Stack direction="row" flexWrap="wrap" gap={1}>
              <Button
                onClick={() => setCloning(true)}
                startIcon={<ContentCopyOutlinedIcon fontSize="small" />}
                variant="outlined"
              >
                Clonar en ciclo nuevo
              </Button>
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
                Nueva asignación
              </Button>
            </Stack>
          ) : null
        }
        breadcrumb="Estructura académica"
        subtitle="Qué docente imparte cada curso en cada sección. Reasignar cierra la asignación vigente y abre una nueva; nada se sobrescribe."
        title="Asignaciones docentes"
      />

      <ListSection
        actionError={actionError}
        columns={columns}
        emptyMessage={
          hasFilters
            ? "Sin asignaciones para los filtros seleccionados."
            : "No hay asignaciones docentes registradas."
        }
        fillHeight
        filters={
          <FilterBar
            onClear={hasFilters ? () => list.setFilters(FILTERS) : undefined}
          >
            <FilterSelect
              emptyLabel="Todos los ciclos"
              label="Ciclo escolar"
              loading={cycles.loading}
              minWidth={220}
              onChange={(value) =>
                list.setFilters({ academic_cycle_id: value, section_id: "" })
              }
              options={cycles.options}
              value={filters.academic_cycle_id}
            />
            <Suspense fallback={null}>
              {filters.academic_cycle_id ? (
                <div style={{ minWidth: 240 }}>
                  <RemoteSearchSelect
                    key={`section-${filters.academic_cycle_id}`}
                    label="Sección"
                    name="section_filter"
                    onChange={(event) =>
                      list.setFilter("section_id", event.target.value)
                    }
                    placeholder="Buscar sección"
                    search={sectionSearch(filters.academic_cycle_id)}
                    value={filters.section_id}
                  />
                </div>
              ) : null}
              <div style={{ minWidth: 240 }}>
                <RemoteSearchSelect
                  label="Docente"
                  name="teacher_filter"
                  onChange={(event) =>
                    list.setFilter("teacher_id", event.target.value)
                  }
                  placeholder="Buscar docente"
                  search={TEACHER_SEARCH}
                  value={filters.teacher_id}
                />
              </div>
            </Suspense>
            <FormControlLabel
              control={
                <Switch
                  checked={filters.current === "true"}
                  onChange={(event) =>
                    list.setFilter(
                      "current",
                      event.target.checked ? "true" : ""
                    )
                  }
                  size="small"
                />
              }
              label="Solo vigentes"
            />
          </FilterBar>
        }
        getRowKey={(row) => row.public_id}
        list={list}
        renderActions={
          canManage
            ? (row) =>
                row.ends_on ? null : (
                  <ActionIconButton
                    label="Reasignar a otro docente"
                    onClick={() => setReassigning(row)}
                  >
                    <SwapHorizOutlinedIcon fontSize="small" />
                  </ActionIconButton>
                )
            : undefined
        }
        showInactiveToggle={false}
        subtitle="Vigentes y finalizadas"
        title="Asignaciones registradas"
      />

      {creating ? (
        <EntityFormWindow
          description="La asignación vincula a un docente con una sección y un curso dentro de un ciclo."
          fields={assignmentFields}
          initialValues={{
            academic_cycle_id: "",
            section_id: "",
            subject_id: "",
            teacher_id: "",
            starts_on: "",
          }}
          onCancel={() => setCreating(false)}
          onSubmit={handleCreate}
          open
          submitLabel="Crear asignación"
          title="Nueva asignación docente"
        />
      ) : null}

      <Suspense fallback={null}>
        {bulkAssigning ? (
          <BulkAssignmentWindow
            onClose={() => setBulkAssigning(false)}
            onCreated={list.refresh}
          />
        ) : null}

        {cloning ? (
          <CloneAssignmentsWindow
            onClose={() => setCloning(false)}
            onCreated={list.refresh}
          />
        ) : null}
      </Suspense>

      {reassigning ? (
        <EntityFormWindow
          description={`${sectionLabel(reassigning.section ?? {})} · ${subjectName(reassigning.subject)}. La asignación actual de ${reassigning.teacher?.name ?? "el docente"} se cierra en la fecha indicada y el docente entrante toma el curso desde el día siguiente.`}
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
