import { useCallback, useMemo, useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";

import { academicsService, PAGE_SIZE } from "@academics/academicsService.js";
import { collectAllPages } from "@shared/api/pages.js";
import { useCatalogOptions } from "@shared/catalogs/useCatalogOptions.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { ConfirmActionButton } from "@ui/buttons/ConfirmActionButton.jsx";
import { ActiveCell, CodeCell, MutedCell } from "@ui/table/cells.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";

const CREATE_FIELDS = (campuses) => [
  {
    name: "campus_id",
    label: "Sede",
    type: "select",
    options: campuses.options,
    loading: campuses.loading,
    optionsError: campuses.error,
    emptyHint: "Registre primero una sede activa.",
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
    label: "Codigo",
    required: true,
    placeholder: "Ejemplo: A-101",
  },
  {
    name: "location",
    label: "Ubicacion",
    placeholder: "Ejemplo: Edificio A, primer nivel",
  },
  {
    name: "capacity",
    label: "Capacidad",
    type: "number",
    min: 0,
    help: "Cantidad maxima de estudiantes; use 0 si aun no esta definida.",
  },
];

const EDIT_FIELDS = [
  { name: "name", label: "Nombre", required: true },
  { name: "location", label: "Ubicacion" },
  { name: "capacity", label: "Capacidad", type: "number", min: 0 },
];

const COLUMNS = [
  { key: "name", label: "Aula", render: (row) => row.name },
  {
    key: "code",
    label: "Codigo",
    render: (row) => <CodeCell value={row.code} />,
  },
  {
    key: "campus",
    label: "Sede",
    render: (row) => row.campus?.name ?? <MutedCell>Sin sede</MutedCell>,
  },
  {
    key: "location",
    label: "Ubicacion",
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

async function loadCampusOptions() {
  const campuses = await collectAllPages(academicsService.listCampuses);
  return campuses
    .sort((left, right) => left.name.localeCompare(right.name, "es"))
    .map((campus) => ({
      value: campus.public_id,
      label: `${campus.name} (${campus.code})`,
    }));
}

/** Catalogo institucional de aulas, laboratorios y otros espacios fisicos. */
export function RoomsPage() {
  const loadRooms = useCallback(
    (params) => academicsService.listClassrooms(params),
    []
  );
  const list = usePaginatedList(loadRooms, { pageSize: PAGE_SIZE });
  const campuses = useCatalogOptions(loadCampusOptions);
  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  const createFields = useMemo(() => CREATE_FIELDS(campuses), [campuses]);

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
        subtitle="Registre los espacios fisicos donde se desarrollan las actividades academicas. La baja conserva el historial y solo desactiva el aula."
        title="Aulas y espacios"
      />

      <ListSection
        action={
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
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nueva aula
          </Button>
        }
        actionError={actionError}
        columns={COLUMNS}
        emptyMessage="Todavia no hay aulas ni espacios registrados."
        getRowKey={(room) => room.public_id}
        list={list}
        renderActions={(room) => (
          <Stack direction="row" gap={0.5} justifyContent="flex-end">
            <ActionIconButton
              label="Editar"
              onClick={() => setEditing({ mode: "edit", room })}
            >
              <EditOutlinedIcon fontSize="small" />
            </ActionIconButton>
            {room.is_active ? (
              <ConfirmActionButton
                confirmLabel="Si, desactivar"
                label="Desactivar"
                onConfirm={() => handleDeactivate(room)}
                question={`Se desactivara "${room.name}". El historial se conservara.`}
                title="Desactivar aula"
              />
            ) : null}
          </Stack>
        )}
        subtitle="Catalogo de espacios fisicos por sede"
        title="Aulas registradas"
      />

      {editing?.mode === "create" ? (
        <EntityFormWindow
          description="El codigo identifica el aula dentro de la sede y no puede cambiarse despues de registrarla."
          fields={createFields}
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

      {editing?.mode === "edit" ? (
        <EntityFormWindow
          description={`El codigo ${editing.room.code} y la sede son inmutables para preservar la trazabilidad.`}
          fields={EDIT_FIELDS}
          initialValues={{
            name: editing.room.name,
            location: editing.room.location || "",
            capacity: editing.room.capacity,
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
