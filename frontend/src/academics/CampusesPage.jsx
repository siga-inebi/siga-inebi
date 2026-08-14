import { useCallback, useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";

import { academicsService, PAGE_SIZE } from "@academics/academicsService.js";
import { EntityFormDrawer } from "@shared/crud/EntityFormDrawer.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { ConfirmActionButton } from "@ui/buttons/ConfirmActionButton.jsx";
import { ActiveCell, BooleanCell, CodeCell, MutedCell } from "@ui/table/cells.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";

const CAMPUS_COLUMNS = [
  { key: "name", label: "Sede", render: (row) => row.name },
  { key: "code", label: "Codigo", render: (row) => <CodeCell value={row.code} /> },
  {
    key: "address",
    label: "Direccion",
    render: (row) => row.address || <MutedCell>Sin registrar</MutedCell>,
  },
  { key: "is_main", label: "Principal", render: (row) => <BooleanCell value={row.is_main} /> },
  { key: "shift_count", label: "Jornadas", align: "right", render: (row) => row.shift_count },
  {
    key: "is_active",
    label: "Estado",
    render: (row) => <ActiveCell active={row.is_active} inactiveLabel="Desactivada" />,
  },
];

const CREATE_CAMPUS_FIELDS = [
  { name: "name", label: "Nombre", required: true, placeholder: "Ejemplo: Sede Central" },
  { name: "code", label: "Codigo", required: true, placeholder: "Ejemplo: CENTRAL" },
  { name: "address", label: "Direccion (opcional)" },
  {
    name: "is_main",
    label: "Es la sede principal",
    type: "checkbox",
    help: "Solo puede haber una; marcarla degrada a la anterior.",
  },
];

const EDIT_CAMPUS_FIELDS = [
  { name: "name", label: "Nombre", required: true },
  { name: "address", label: "Direccion (opcional)" },
  { name: "is_main", label: "Es la sede principal", type: "checkbox" },
];

export function CampusesPage() {
  const loadCampuses = useCallback((params) => academicsService.listCampuses(params), []);
  const list = usePaginatedList(loadCampuses, { pageSize: PAGE_SIZE });

  const [editing, setEditing] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [actionError, setActionError] = useState("");

  // La sede seleccionada se re-lee del listado para que no quede desfasada
  // despues de editarla o de recargar la pagina de resultados.
  const selected =
    list.items.find((campus) => campus.public_id === selectedId) || null;

  const handleCreate = async (payload) => {
    await academicsService.createCampus(payload);
    setEditing(null);
    list.refresh();
  };

  const handleUpdate = async (payload) => {
    await academicsService.updateCampus(editing.campus.public_id, payload);
    setEditing(null);
    list.refresh();
  };

  const handleDeactivate = async (campus) => {
    setActionError("");
    try {
      await academicsService.deactivateCampus(campus.public_id);
      if (campus.public_id === selectedId) setSelectedId("");
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
        subtitle="Registra las sedes del establecimiento y las jornadas que atiende cada una. Dar de baja una sede la desactiva junto con sus jornadas."
        title="Sedes y jornadas"
      />

      <ListSection
        action={
          <Button
            onClick={() => setEditing({ mode: "create" })}
            size="small"
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nueva sede
          </Button>
        }
        actionError={actionError}
        list={list}
        columns={CAMPUS_COLUMNS}
        emptyMessage="Todavia no hay sedes registradas."
        getRowKey={(campus) => campus.public_id}
        renderActions={(campus) => (
          <Stack direction="row" gap={0.5} justifyContent="flex-end">
            <ActionIconButton
              color={campus.public_id === selectedId ? "primary" : "default"}
              label={
                campus.public_id === selectedId ? "Ocultar jornadas" : "Ver jornadas"
              }
              onClick={() =>
                setSelectedId(campus.public_id === selectedId ? "" : campus.public_id)
              }
            >
              <ScheduleOutlinedIcon fontSize="small" />
            </ActionIconButton>
            <ActionIconButton
              label="Editar"
              onClick={() => setEditing({ mode: "edit", campus })}
            >
              <EditOutlinedIcon fontSize="small" />
            </ActionIconButton>
            {campus.is_active ? (
              <ConfirmActionButton
                confirmLabel="Si, desactivar"
                label="Desactivar"
                onConfirm={() => handleDeactivate(campus)}
                question={`Se desactivara "${campus.name}" junto con todas sus jornadas.`}
                title="Desactivar sede"
              />
            ) : null}
          </Stack>
        )}
        subtitle="Sedes de la institucion"
        title="Sedes registradas"
      />

      {selected ? (
        <CampusShiftsSection
          campus={selected}
          key={selected.public_id}
          onChanged={list.refresh}
        />
      ) : null}

      <EntityFormDrawer
        description="El codigo se normaliza a mayusculas y no se puede cambiar despues."
        fields={CREATE_CAMPUS_FIELDS}
        initialValues={{ name: "", code: "", address: "", is_main: false }}
        key={editing?.mode === "create" ? "create-open" : "create-closed"}
        onCancel={() => setEditing(null)}
        onSubmit={handleCreate}
        open={editing?.mode === "create"}
        submitLabel="Crear sede"
        title="Nueva sede"
      />

      {editing?.mode === "edit" ? (
        <EntityFormDrawer
          description={`El codigo ${editing.campus.code} es inmutable.`}
          fields={EDIT_CAMPUS_FIELDS}
          initialValues={{
            name: editing.campus.name,
            address: editing.campus.address || "",
            is_main: editing.campus.is_main,
          }}
          key={editing.campus.public_id}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          open
          submitLabel="Guardar cambios"
          title={`Editar ${editing.campus.name}`}
        />
      ) : null}
    </>
  );
}

const SHIFT_COLUMNS = [
  { key: "name", label: "Jornada", render: (row) => row.name },
  { key: "code", label: "Codigo", render: (row) => <CodeCell value={row.code} /> },
  {
    key: "is_active",
    label: "Estado",
    render: (row) => <ActiveCell active={row.is_active} inactiveLabel="Desactivada" />,
  },
];

const CREATE_SHIFT_FIELDS = [
  { name: "name", label: "Nombre", required: true, placeholder: "Ejemplo: Matutina" },
  { name: "code", label: "Codigo", required: true, placeholder: "Ejemplo: MAT" },
];

const EDIT_SHIFT_FIELDS = [{ name: "name", label: "Nombre", required: true }];

/**
 * Jornadas de una sede. Se remonta con `key` al cambiar de sede, de modo que la
 * paginacion y el formulario arrancan limpios.
 */
function CampusShiftsSection({ campus, onChanged }) {
  const loadShifts = useCallback(
    (params) => academicsService.listCampusShifts(campus.public_id, params),
    [campus.public_id]
  );
  const list = usePaginatedList(loadShifts, { pageSize: PAGE_SIZE });

  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  const afterChange = () => {
    setEditing(null);
    list.refresh();
    onChanged();
  };

  const handleCreate = async (payload) => {
    await academicsService.createShift(campus.public_id, payload);
    afterChange();
  };

  const handleUpdate = async (payload) => {
    await academicsService.updateShift(editing.shift.public_id, payload);
    afterChange();
  };

  const handleDeactivate = async (shift) => {
    setActionError("");
    try {
      await academicsService.deactivateShift(shift.public_id);
      afterChange();
    } catch (requestError) {
      setActionError(requestError.message);
      throw requestError;
    }
  };

  return (
    <>
      <ListSection
        action={
          <Button
            onClick={() => setEditing({ mode: "create" })}
            size="small"
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nueva jornada
          </Button>
        }
        actionError={actionError}
        list={list}
        columns={SHIFT_COLUMNS}
        emptyMessage="Esta sede todavia no tiene jornadas."
        getRowKey={(shift) => shift.public_id}
        renderActions={(shift) => (
          <Stack direction="row" gap={0.5} justifyContent="flex-end">
            <ActionIconButton
              label="Editar"
              onClick={() => setEditing({ mode: "edit", shift })}
            >
              <EditOutlinedIcon fontSize="small" />
            </ActionIconButton>
            {shift.is_active ? (
              <ConfirmActionButton
                confirmLabel="Si, desactivar"
                label="Desactivar"
                onConfirm={() => handleDeactivate(shift)}
                question={`Se desactivara la jornada "${shift.name}".`}
                title="Desactivar jornada"
              />
            ) : null}
          </Stack>
        )}
        subtitle={campus.name}
        title="Jornadas de la sede"
      />

      <EntityFormDrawer
        description="El codigo es unico dentro de la sede: dos sedes pueden tener MAT."
        fields={CREATE_SHIFT_FIELDS}
        initialValues={{ name: "", code: "" }}
        key={editing?.mode === "create" ? "shift-create-open" : "shift-create-closed"}
        onCancel={() => setEditing(null)}
        onSubmit={handleCreate}
        open={editing?.mode === "create"}
        submitLabel="Crear jornada"
        title="Nueva jornada"
      />

      {editing?.mode === "edit" ? (
        <EntityFormDrawer
          description="Solo se puede renombrar; el codigo es inmutable."
          fields={EDIT_SHIFT_FIELDS}
          initialValues={{ name: editing.shift.name }}
          key={editing.shift.public_id}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          open
          submitLabel="Guardar cambios"
          title={`Editar ${editing.shift.name}`}
        />
      ) : null}
    </>
  );
}
