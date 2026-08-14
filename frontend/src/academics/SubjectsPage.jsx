import { useCallback, useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";

import { academicsService, PAGE_SIZE } from "@academics/academicsService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { ConfirmActionButton } from "@ui/buttons/ConfirmActionButton.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { ActiveCell, CodeCell, MutedCell } from "@ui/table/cells.jsx";

const SUBJECT_COLUMNS = [
  { key: "name", label: "Curso", render: (row) => row.name },
  { key: "code", label: "Codigo", render: (row) => <CodeCell value={row.code} /> },
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

export function SubjectsPage() {
  const loadSubjects = useCallback((params) => academicsService.listSubjects(params), []);
  const list = usePaginatedList(loadSubjects, { pageSize: PAGE_SIZE });

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
        breadcrumb="Estructura academica"
        subtitle="Catalogo de cursos de la institucion. Los niveles en los que se imparte cada uno se declaran desde el plan de estudios del nivel."
        title="Cursos"
      />

      <ListSection
        action={
          <Button
            onClick={() => setEditing({ mode: "create" })}
            size="small"
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nuevo curso
          </Button>
        }
        actionError={actionError}
        list={list}
        columns={SUBJECT_COLUMNS}
        emptyMessage="Todavia no hay cursos registrados."
        fillHeight
        getRowKey={(subject) => subject.public_id}
        renderActions={(subject) => (
          <Stack direction="row" gap={0.5} justifyContent="flex-end">
            <ActionIconButton
              label="Editar"
              onClick={() => setEditing({ mode: "edit", subject })}
            >
              <EditOutlinedIcon fontSize="small" />
            </ActionIconButton>
            {subject.is_active ? (
              <ConfirmActionButton
                confirmLabel="Si, desactivar"
                label="Desactivar"
                onConfirm={() => handleDeactivate(subject)}
                question={`Se desactivara "${subject.name}". Podra reactivarse despues, pero dejara de estar disponible en el plan de estudios.`}
                title="Desactivar curso"
              />
            ) : null}
          </Stack>
        )}
        subtitle="Cursos de la institucion"
        title="Cursos registrados"
      />

      {/* Los formularios se remontan por `key` al abrir para que su estado nazca
          limpio; renovar la key al cerrar mostraria el form vacio durante la
          animacion de salida. */}
      <EntityFormWindow
        description="El codigo es unico por institucion y no se puede cambiar despues."
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
          description={`El codigo ${editing.subject.code} es inmutable.`}
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
  { name: "name", label: "Nombre", required: true, placeholder: "Ejemplo: Matematica" },
  { name: "code", label: "Codigo", required: true, placeholder: "Ejemplo: MAT" },
];

const EDIT_FIELDS = [{ name: "name", label: "Nombre", required: true }];
