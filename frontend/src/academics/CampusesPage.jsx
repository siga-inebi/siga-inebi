import { useState } from "react";
import { useSearchParams } from "react-router-dom";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";

import { academicsService } from "@academics/academicsService.js";
import {
  CatalogFilters,
  DetailToggleButton,
} from "@academics/CatalogFilters.jsx";
import { NAME_CODE_ORDERING } from "@academics/catalogOrdering.js";
import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { suggestedOrBlank } from "@shared/crud/suggestion.js";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { ConfirmActionButton } from "@ui/buttons/ConfirmActionButton.jsx";
import {
  ActiveCell,
  BooleanCell,
  CodeCell,
  MutedCell,
} from "@ui/table/cells.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";

const CAMPUS_COLUMNS = [
  { key: "name", label: "Sede", render: (row) => row.name },
  {
    key: "code",
    label: "Código",
    render: (row) => <CodeCell value={row.code} />,
  },
  {
    key: "address",
    label: "Dirección",
    render: (row) => row.address || <MutedCell>Sin registrar</MutedCell>,
  },
  {
    key: "is_main",
    label: "Principal",
    render: (row) => <BooleanCell value={row.is_main} />,
  },
  {
    key: "shift_count",
    label: "Jornadas",
    align: "right",
    render: (row) => row.shift_count,
  },
  {
    key: "is_active",
    label: "Estado",
    render: (row) => (
      <ActiveCell active={row.is_active} inactiveLabel="Desactivada" />
    ),
  },
];

const CREATE_CAMPUS_FIELDS = [
  {
    name: "name",
    label: "Nombre",
    required: true,
    placeholder: "Ejemplo: Sede Central",
  },
  {
    name: "code",
    label: "Código",
    help: "Se genera solo. Cámbielo si la sede ya se conoce por otro código.",
  },
  { name: "address", label: "Dirección (opcional)" },
  {
    name: "is_main",
    label: "Es la sede principal",
    type: "checkbox",
    help: "Solo puede haber una; marcarla degrada a la anterior.",
  },
];

const EDIT_CAMPUS_FIELDS = [
  { name: "name", label: "Nombre", required: true },
  { name: "address", label: "Dirección (opcional)" },
  { name: "is_main", label: "Es la sede principal", type: "checkbox" },
];

/**
 * Sedes y sus jornadas (A1–A3). Ambos listados se piden por página al servidor
 * con búsqueda, orden e inactivas en la URL; la sede elegida también
 * (`?sede=<id>`), así recargar o compartir el enlace conserva la vista.
 */
export function CampusesPage() {
  const { can } = usePermissions();
  const canEdit = can(PERMISSION.SCOPE_ASSIGN);
  const [searchParams, setSearchParams] = useSearchParams();
  const list = useServerList({
    queryKey: queryKeys.academics.list("campuses"),
    fetchPage: (params) => academicsService.listCampuses(params),
    defaultOrdering: "name",
    canIncludeInactive: true,
  });

  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");
  const selectedId = searchParams.get("sede") ?? "";
  const setSelectedId = (campusId) =>
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        // Las jornadas de otra sede no comparten pagina ni busqueda.
        for (const key of [...next.keys()]) {
          if (key.startsWith("shifts_")) next.delete(key);
        }
        if (campusId) next.set("sede", campusId);
        else next.delete("sede");
        return next;
      },
      { replace: true }
    );
  const toggle = (campus) =>
    setSelectedId(campus.public_id === selectedId ? "" : campus.public_id);

  // La sede seleccionada se re-lee del listado para que no quede desfasada
  // despues de editarla o de recargar la pagina de resultados.
  const inPage =
    list.items.find((campus) => campus.public_id === selectedId) || null;
  // Un enlace compartido puede apuntar a una sede de otra pagina o filtro.
  const fallback = useResourceQuery(
    queryKeys.academics.list("campus", selectedId),
    () => academicsService.getCampus(selectedId),
    { enabled: Boolean(selectedId) && !inPage && !list.loading }
  );
  const selected = inPage ?? (selectedId ? fallback.data : null) ?? null;

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
        subtitle="Registre las sedes del establecimiento y las jornadas que atiende cada una. Dar de baja una sede la desactiva junto con sus jornadas."
        title="Sedes y jornadas"
      />

      <ListSection
        action={
          canEdit ? (
            <Button
              onClick={async () =>
                setEditing({
                  mode: "create",
                  values: {
                    name: "",
                    code: await suggestedOrBlank(
                      academicsService.nextCampusCode
                    ),
                    address: "",
                    is_main: false,
                  },
                })
              }
              size="small"
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Nueva sede
            </Button>
          ) : null
        }
        actionError={actionError}
        list={list}
        columns={CAMPUS_COLUMNS}
        filters={
          <CatalogFilters
            list={list}
            orderingOptions={NAME_CODE_ORDERING}
            placeholder="Buscar sede por nombre o código"
          />
        }
        onRowClick={toggle}
        emptyMessage={
          list.search
            ? "Sin sedes para los filtros seleccionados."
            : "Todavía no hay sedes registradas."
        }
        getRowKey={(campus) => campus.public_id}
        renderActions={(campus) => (
          <Stack direction="row" gap={0.5} justifyContent="flex-end">
            <DetailToggleButton
              count={campus.shift_count}
              noun="jornadas"
              onToggle={() => toggle(campus)}
              open={campus.public_id === selectedId}
            />
            {canEdit ? (
              <ActionIconButton
                label="Editar"
                onClick={() => setEditing({ mode: "edit", campus })}
              >
                <EditOutlinedIcon fontSize="small" />
              </ActionIconButton>
            ) : null}
            {canEdit && campus.is_active ? (
              <ConfirmActionButton
                confirmLabel="Sí, desactivar"
                label="Desactivar"
                onConfirm={() => handleDeactivate(campus)}
                question={`Se desactivará "${campus.name}" junto con todas sus jornadas.`}
                title="Desactivar sede"
              />
            ) : null}
          </Stack>
        )}
        subtitle="Elija «Ver jornadas» o haga clic en una sede para administrar sus jornadas."
        title="Sedes registradas"
      />

      {selected ? (
        <CampusShiftsSection
          campus={selected}
          canEdit={canEdit}
          key={selected.public_id}
          onChanged={list.refresh}
        />
      ) : null}

      {editing?.mode === "create" ? (
        <EntityFormWindow
          description="El código se sugiere solo y no se puede cambiar después de crear la sede."
          fields={CREATE_CAMPUS_FIELDS}
          initialValues={editing.values}
          onCancel={() => setEditing(null)}
          onSubmit={handleCreate}
          open
          submitLabel="Crear sede"
          title="Nueva sede"
        />
      ) : null}

      {editing?.mode === "edit" ? (
        <EntityFormWindow
          description={`El código ${editing.campus.code} no se puede cambiar.`}
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
  {
    key: "code",
    label: "Código",
    render: (row) => <CodeCell value={row.code} />,
  },
  {
    key: "is_active",
    label: "Estado",
    render: (row) => (
      <ActiveCell active={row.is_active} inactiveLabel="Desactivada" />
    ),
  },
];

const CREATE_SHIFT_FIELDS = [
  {
    name: "name",
    label: "Nombre",
    required: true,
    placeholder: "Ejemplo: Matutina",
  },
  {
    name: "code",
    label: "Código",
    required: true,
    placeholder: "Ejemplo: MAT",
  },
];

const EDIT_SHIFT_FIELDS = [{ name: "name", label: "Nombre", required: true }];

/**
 * Jornadas de una sede. Se remonta con `key` al cambiar de sede, de modo que la
 * paginacion y el formulario arrancan limpios.
 */
function CampusShiftsSection({ campus, canEdit, onChanged }) {
  const list = useServerList({
    queryKey: queryKeys.academics.list("shifts", campus.public_id),
    fetchPage: (params) =>
      academicsService.listCampusShifts(campus.public_id, params),
    defaultOrdering: "name",
    canIncludeInactive: true,
    urlPrefix: "shifts_",
  });

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
          canEdit ? (
            <Button
              onClick={() => setEditing({ mode: "create" })}
              size="small"
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Nueva jornada
            </Button>
          ) : null
        }
        actionError={actionError}
        list={list}
        columns={SHIFT_COLUMNS}
        filters={
          <CatalogFilters
            list={list}
            orderingOptions={NAME_CODE_ORDERING}
            placeholder="Buscar jornada por nombre o código"
          />
        }
        emptyMessage={
          list.search
            ? "Sin jornadas para los filtros seleccionados."
            : "Esta sede todavía no tiene jornadas."
        }
        getRowKey={(shift) => shift.public_id}
        renderActions={
          canEdit
            ? (shift) => (
                <Stack direction="row" gap={0.5} justifyContent="flex-end">
                  <ActionIconButton
                    label="Editar"
                    onClick={() => setEditing({ mode: "edit", shift })}
                  >
                    <EditOutlinedIcon fontSize="small" />
                  </ActionIconButton>
                  {shift.is_active ? (
                    <ConfirmActionButton
                      confirmLabel="Sí, desactivar"
                      label="Desactivar"
                      onConfirm={() => handleDeactivate(shift)}
                      question={`Se desactivará la jornada "${shift.name}".`}
                      title="Desactivar jornada"
                    />
                  ) : null}
                </Stack>
              )
            : undefined
        }
        subtitle={campus.name}
        title={`Jornadas de ${campus.name}`}
      />

      <EntityFormWindow
        description="El código es único dentro de la sede: dos sedes pueden tener MAT."
        fields={CREATE_SHIFT_FIELDS}
        initialValues={{ name: "", code: "" }}
        key={
          editing?.mode === "create"
            ? "shift-create-open"
            : "shift-create-closed"
        }
        onCancel={() => setEditing(null)}
        onSubmit={handleCreate}
        open={editing?.mode === "create"}
        submitLabel="Crear jornada"
        title="Nueva jornada"
      />

      {editing?.mode === "edit" ? (
        <EntityFormWindow
          description="Solo se puede renombrar; el código no cambia."
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
