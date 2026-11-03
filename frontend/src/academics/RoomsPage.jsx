import { useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";

import { academicsService } from "@academics/academicsService.js";
import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { ConfirmActionButton } from "@ui/buttons/ConfirmActionButton.jsx";
import { ActiveCell, CodeCell, MutedCell } from "@ui/table/cells.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";

import { BulkClassroomWindow } from "./BulkClassroomWindow.jsx";

/** Sedes con búsqueda en el servidor: no se descarga el catálogo completo. */
const CAMPUS_SEARCH = {
  name: "campuses",
  fetchPage: (params) => academicsService.listCampuses(params),
  mapResult: (campus) => ({
    value: campus.public_id,
    label: `${campus.name} (${campus.code})`,
  }),
};

const CREATE_FIELDS = [
  {
    name: "campus_id",
    label: "Sede",
    type: "search-select",
    search: CAMPUS_SEARCH,
    help: "Escriba el nombre o el código de la sede.",
    required: true,
    span: "full",
  },
  {
    name: "name",
    label: "Nombre",
    required: true,
    placeholder: "Ejemplo: Aula 1",
  },
  {
    name: "code",
    label: "Código",
    required: true,
    placeholder: "Ejemplo: A-101",
  },
  {
    name: "location",
    label: "Ubicación",
    placeholder: "Ejemplo: Edificio A, primer nivel",
  },
  {
    name: "capacity",
    label: "Capacidad",
    type: "number",
    min: 0,
    help: "Cantidad máxima de estudiantes; use 0 si aún no está definida.",
  },
];

const SERVICE_STATUS_OPTIONS = [
  { value: "available", label: "Disponible" },
  { value: "unavailable", label: "Temporalmente inhabilitada" },
  { value: "maintenance", label: "En mantenimiento" },
];

const EDIT_FIELDS = [
  { name: "name", label: "Nombre", required: true },
  { name: "location", label: "Ubicación" },
  { name: "capacity", label: "Capacidad", type: "number", min: 0 },
  {
    name: "service_status",
    label: "Disponibilidad",
    type: "select",
    options: SERVICE_STATUS_OPTIONS,
    required: true,
    help: "Fuera de servicio se bloquean nuevas asignaciones. Las sesiones existentes se conservan.",
  },
];

const COLUMNS = [
  { key: "name", label: "Aula", render: (row) => row.name },
  {
    key: "service_status",
    label: "Disponibilidad",
    render: (row) =>
      SERVICE_STATUS_OPTIONS.find(
        (option) => option.value === (row.service_status ?? "available")
      )?.label,
  },
  {
    key: "code",
    label: "Código",
    render: (row) => <CodeCell value={row.code} />,
  },
  {
    key: "campus",
    label: "Sede",
    render: (row) => row.campus?.name ?? <MutedCell>Sin sede</MutedCell>,
  },
  {
    key: "location",
    label: "Ubicación",
    render: (row) => row.location || <MutedCell>Sin registrar</MutedCell>,
  },
  {
    key: "capacity",
    label: "Capacidad",
    align: "right",
    render: (row) => row.capacity || <MutedCell>Sin definir</MutedCell>,
  },
  {
    key: "is_active",
    label: "Estado",
    render: (row) => (
      <ActiveCell active={row.is_active} inactiveLabel="Desactivada" />
    ),
  },
];

const ROOM_ORDERING = [
  { value: "name", label: "Nombre (A–Z)" },
  { value: "-name", label: "Nombre (Z–A)" },
  { value: "code", label: "Código (A–Z)" },
  { value: "campus", label: "Sede" },
  { value: "-capacity", label: "Capacidad (mayor primero)" },
  { value: "capacity", label: "Capacidad (menor primero)" },
];

/** Una sola página de sedes basta para el filtro: son pocas por definición. */
const CAMPUS_FILTER_PAGE = { page: 1, page_size: 100 };

/**
 * Catálogo institucional de aulas, laboratorios y otros espacios físicos.
 *
 * Listado en el servidor (página, búsqueda, orden, sede e inactivas en la
 * URL). La sede viene anidada en cada aula (A2): no se descargan las sedes para
 * pintar su nombre.
 */
export function RoomsPage() {
  const { can } = usePermissions();
  const canEdit = can(PERMISSION.SCOPE_ASSIGN);
  const list = useServerList({
    queryKey: queryKeys.academics.list("classrooms"),
    fetchPage: (params) => academicsService.listClassrooms(params),
    defaultFilters: { campus_id: "" },
    defaultOrdering: "name",
    canIncludeInactive: true,
  });
  const campuses = useResourceQuery(
    queryKeys.academics.list("campuses", "filter"),
    () => academicsService.listCampuses(CAMPUS_FILTER_PAGE),
    { defaultData: null }
  );
  const campusOptions = (campuses.data?.results ?? []).map((campus) => ({
    value: campus.public_id,
    label: campus.name,
  }));
  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");
  const hasFilters = Boolean(list.search || list.filters.campus_id);

  const afterChange = () => {
    setEditing(null);
    list.refresh();
  };

  const handleDeactivate = async (room) => {
    setActionError("");
    try {
      await academicsService.deactivateClassroom(room.public_id);
      list.refresh();
    } catch (requestError) {
      setActionError(requestError.message);
      throw requestError;
    }
  };

  return (
    <>
      <PageHeader
        breadcrumb="Estructura institucional"
        subtitle="Registre los espacios físicos donde se desarrollan las actividades académicas. La baja conserva el historial y solo desactiva el aula."
        title="Aulas y espacios"
      />

      <ListSection
        action={
          canEdit ? (
            <Stack direction="row" gap={1}>
              <Button
                onClick={() => setEditing({ mode: "batch" })}
                size="small"
                startIcon={<AddIcon fontSize="small" />}
                variant="contained"
              >
                Crear por lote
              </Button>
              <Button
                onClick={() =>
                  setEditing({
                    mode: "create",
                    values: {
                      campus_id: "",
                      name: "",
                      code: "",
                      location: "",
                      capacity: 0,
                    },
                  })
                }
                size="small"
              >
                Nueva aula
              </Button>
            </Stack>
          ) : null
        }
        actionError={actionError}
        columns={COLUMNS}
        emptyMessage={
          hasFilters
            ? "Sin aulas para los filtros seleccionados."
            : "Todavía no hay aulas ni espacios registrados."
        }
        filters={
          <FilterBar
            onClear={
              hasFilters
                ? () => {
                    list.setSearch("");
                    list.setFilter("campus_id", "");
                  }
                : undefined
            }
          >
            <SearchField
              debounceMs={0}
              onChange={list.setSearch}
              placeholder="Buscar por nombre o código"
              value={list.search}
            />
            <FilterSelect
              emptyLabel="Todas las sedes"
              label="Sede"
              loading={campuses.loading}
              onChange={(value) => list.setFilter("campus_id", value)}
              options={campusOptions}
              value={list.filters.campus_id}
            />
            <FilterSelect
              label="Ordenar por"
              onChange={list.setOrdering}
              options={ROOM_ORDERING}
              value={list.ordering}
            />
          </FilterBar>
        }
        getRowKey={(room) => room.public_id}
        list={list}
        renderActions={
          canEdit
            ? (room) => (
                <Stack direction="row" gap={0.5} justifyContent="flex-end">
                  <ActionIconButton
                    label="Editar"
                    onClick={() => setEditing({ mode: "edit", room })}
                  >
                    <EditOutlinedIcon fontSize="small" />
                  </ActionIconButton>
                  {room.is_active ? (
                    <ConfirmActionButton
                      confirmLabel="Sí, desactivar"
                      label="Desactivar"
                      onConfirm={() => handleDeactivate(room)}
                      question={`Se desactivará "${room.name}". El historial se conservará.`}
                      title="Desactivar aula"
                    />
                  ) : null}
                </Stack>
              )
            : undefined
        }
        subtitle="Catálogo de espacios físicos por sede"
        title="Aulas registradas"
      />

      {editing?.mode === "create" ? (
        <EntityFormWindow
          description="El código identifica el aula dentro de la sede y no puede cambiarse después de registrarla."
          fields={CREATE_FIELDS}
          initialValues={editing.values}
          onCancel={() => setEditing(null)}
          onSubmit={async (payload) => {
            await academicsService.createClassroom(payload);
            afterChange();
          }}
          open
          submitLabel="Crear aula"
          title="Nueva aula"
        />
      ) : null}

      {editing?.mode === "batch" ? (
        <BulkClassroomWindow
          onCancel={() => setEditing(null)}
          onCreated={afterChange}
        />
      ) : null}

      {editing?.mode === "edit" ? (
        <EntityFormWindow
          description={`El código ${editing.room.code} y la sede no cambian, para preservar la trazabilidad.`}
          fields={EDIT_FIELDS}
          initialValues={{
            name: editing.room.name,
            location: editing.room.location || "",
            capacity: editing.room.capacity,
            service_status: editing.room.service_status ?? "available",
          }}
          key={editing.room.public_id}
          onCancel={() => setEditing(null)}
          onSubmit={async (payload) => {
            await academicsService.updateClassroom(
              editing.room.public_id,
              payload
            );
            afterChange();
          }}
          open
          submitLabel="Guardar cambios"
          title={`Editar ${editing.room.name}`}
        />
      ) : null}
    </>
  );
}
