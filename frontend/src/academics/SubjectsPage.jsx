import { useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";

import { academicsService } from "@academics/academicsService.js";
import { CatalogFilters } from "@academics/CatalogFilters.jsx";
import { NAME_CODE_ORDERING } from "@academics/catalogOrdering.js";
import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { ConfirmActionButton } from "@ui/buttons/ConfirmActionButton.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { ActiveCell, CodeCell, MutedCell } from "@ui/table/cells.jsx";

const SUBJECT_COLUMNS = [
  { key: "name", label: "Curso", render: (row) => row.name },
  {
    key: "code",
    label: "Código",
    render: (row) => <CodeCell value={row.code} />,
  },
  {
    key: "levels",
    label: "Se imparte en",
    render: (row) =>
      row.levels?.length ? (
        row.levels.map((level) => level.name).join(", ")
      ) : (
        <MutedCell>Sin vincular</MutedCell>
      ),
  },
  {
    key: "is_active",
    label: "Estado",
    render: (row) => <ActiveCell active={row.is_active} />,
  },
];

/**
 * Catálogo de cursos de la institución. Listado en el servidor con búsqueda,
 * orden e inactivos en la URL (docs/ux-ui.md 1.1, N1).
 */
export function SubjectsPage() {
  const { can } = usePermissions();
  const canEdit = can(PERMISSION.SCOPE_ASSIGN);
  const list = useServerList({
    queryKey: queryKeys.academics.list("subjects"),
    fetchPage: (params) => academicsService.listSubjects(params),
    defaultOrdering: "name",
    canIncludeInactive: true,
  });

  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  const handleCreate = async (payload) => {
    await academicsService.createSubject(payload);
    setEditing(null);
    list.refresh();
  };

  const handleUpdate = async (payload) => {
    await academicsService.updateSubject(editing.subject.public_id, payload);
    setEditing(null);
    list.refresh();
  };

  const handleDeactivate = async (subject) => {
    setActionError("");
    try {
      await academicsService.deactivateSubject(subject.public_id);
      list.refresh();
    } catch (requestError) {
      setActionError(requestError.message);
      throw requestError;
    }
  };

  return (
    <>
      <PageHeader
        breadcrumb="Estructura académica"
        subtitle="Catálogo de cursos de la institución. Los niveles en los que se imparte cada uno se declaran en Niveles → «Cursos del nivel»."
        title="Cursos"
      />

      <ListSection
        action={
          canEdit ? (
            <Button
              onClick={() => setEditing({ mode: "create" })}
              size="small"
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Nuevo curso
            </Button>
          ) : null
        }
        actionError={actionError}
        list={list}
        columns={SUBJECT_COLUMNS}
        emptyMessage={
          list.search
            ? "Sin cursos para los filtros seleccionados."
            : "Todavía no hay cursos registrados."
        }
        filters={
          <CatalogFilters
            list={list}
            orderingOptions={NAME_CODE_ORDERING}
            placeholder="Buscar curso por nombre o código"
          />
        }
        fillHeight
        getRowKey={(subject) => subject.public_id}
        renderActions={
          canEdit
            ? (subject) => (
                <Stack direction="row" gap={0.5} justifyContent="flex-end">
                  <ActionIconButton
                    label="Editar"
                    onClick={() => setEditing({ mode: "edit", subject })}
                  >
                    <EditOutlinedIcon fontSize="small" />
                  </ActionIconButton>
                  {subject.is_active ? (
                    <ConfirmActionButton
                      confirmLabel="Sí, desactivar"
                      label="Desactivar"
                      onConfirm={() => handleDeactivate(subject)}
                      question={`Se desactivará "${subject.name}". Dejará de estar disponible para los cursos del nivel y el plan de estudios de los ciclos.`}
                      title="Desactivar curso"
                    />
                  ) : null}
                </Stack>
              )
            : undefined
        }
        subtitle="Cursos de la institución"
        title="Cursos registrados"
      />

      {/* Los formularios se remontan por `key` al abrir para que su estado nazca
          limpio; renovar la key al cerrar mostraria el form vacio durante la
          animacion de salida. */}
      <EntityFormWindow
        description="El código es único por institución y no se puede cambiar después."
        fields={CREATE_FIELDS}
        initialValues={{ name: "", code: "" }}
        key={editing?.mode === "create" ? "create" : "create-closed"}
        onCancel={() => setEditing(null)}
        onSubmit={handleCreate}
        open={editing?.mode === "create"}
        submitLabel="Crear curso"
        title="Nuevo curso"
      />

      {editing?.mode === "edit" ? (
        <EntityFormWindow
          description={`El código ${editing.subject.code} no se puede cambiar.`}
          fields={EDIT_FIELDS}
          initialValues={{ name: editing.subject.name }}
          key={editing.subject.public_id}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          open
          submitLabel="Guardar cambios"
          title={`Editar ${editing.subject.name}`}
        />
      ) : null}
    </>
  );
}

const CREATE_FIELDS = [
  {
    name: "name",
    label: "Nombre",
    required: true,
    placeholder: "Ejemplo: Matemática",
  },
  {
    name: "code",
    label: "Código",
    required: true,
    placeholder: "Ejemplo: MAT",
  },
];

const EDIT_FIELDS = [{ name: "name", label: "Nombre", required: true }];
