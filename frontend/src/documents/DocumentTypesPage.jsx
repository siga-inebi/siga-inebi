import { useCallback, useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";

import { PAGE_SIZE } from "@academics/academicsService.js";
import { documentsService } from "@documents/documentsService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { ConfirmActionButton } from "@ui/buttons/ConfirmActionButton.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { ActiveCell, CodeCell, MutedCell } from "@ui/table/cells.jsx";

const TYPE_COLUMNS = [
  { key: "label", label: "Tipo", render: (row) => row.label },
  {
    key: "code",
    label: "Codigo",
    render: (row) => <CodeCell value={row.code} />,
  },
  {
    key: "description",
    label: "Descripcion",
    render: (row) => row.description || <MutedCell>Sin descripcion</MutedCell>,
  },
  {
    key: "is_active",
    label: "Estado",
    render: (row) => <ActiveCell active={row.is_active} />,
  },
];

const CREATE_FIELDS = [
  {
    name: "label",
    label: "Nombre visible",
    required: true,
    placeholder: "Ejemplo: Constancia de estudios",
  },
  {
    name: "code",
    label: "Codigo",
    required: true,
    placeholder: "Ejemplo: constancia",
    help: "Minusculas, digitos, guion y guion bajo. No se puede cambiar despues del alta.",
  },
  { name: "description", label: "Descripcion (opcional)", span: "full" },
];

/** El codigo es inmutable despues del alta: el backend no acepta cambiarlo. */
const EDIT_FIELDS = CREATE_FIELDS.filter((field) => field.name !== "code");

/**
 * Catalogo institucional de tipos de documento (RNF-MAN-001).
 *
 * Esta pantalla existe porque los tipos dejaron de estar fijados en codigo: dar
 * de alta un tipo nuevo es una tarea administrativa, no un despliegue. La baja
 * es logica, y el backend la rechaza mientras el tipo tenga plantillas activas,
 * asi que el error se muestra tal cual en vez de adivinarlo aqui.
 */
export function DocumentTypesPage() {
  const loadTypes = useCallback(
    (params) => documentsService.listTypes(params),
    []
  );
  const list = usePaginatedList(loadTypes, { pageSize: PAGE_SIZE });

  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(null);
  const [actionError, setActionError] = useState("");

  const handleCreate = async (payload) => {
    await documentsService.createType(payload);
    setCreating(false);
    list.refresh();
  };

  const handleUpdate = async (payload) => {
    await documentsService.updateType(editing.public_id, payload);
    setEditing(null);
    list.refresh();
  };

  const handleDeactivate = async (kind) => {
    setActionError("");
    try {
      await documentsService.deactivateType(kind.public_id);
      list.refresh();
    } catch (requestError) {
      setActionError(requestError.message);
      throw requestError;
    }
  };

  return (
    <>
      <PageHeader
        action={
          <Button
            onClick={() => setCreating(true)}
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nuevo tipo
          </Button>
        }
        breadcrumb="Documentos"
        subtitle="Tipos de documento que la institucion emite. Se administran aqui, sin cambios en el sistema."
        title="Tipos de documento"
      />

      <ListSection
        actionError={actionError}
        columns={TYPE_COLUMNS}
        emptyMessage="Todavia no hay tipos de documento registrados."
        fillHeight
        getRowKey={(kind) => kind.public_id}
        list={list}
        renderActions={(kind) => (
          <Stack direction="row" gap={0.5} justifyContent="flex-end">
            <ActionIconButton label="Editar" onClick={() => setEditing(kind)}>
              <EditOutlinedIcon fontSize="small" />
            </ActionIconButton>
            {kind.is_active ? (
              <ConfirmActionButton
                confirmLabel="Si, desactivar"
                label="Desactivar"
                onConfirm={() => handleDeactivate(kind)}
                question={`Se desactivara "${kind.label}". Los documentos ya emitidos conservan su tipo; deja de ofrecerse para plantillas nuevas.`}
                title="Desactivar tipo de documento"
              />
            ) : null}
          </Stack>
        )}
        subtitle="Catalogo institucional"
        title="Tipos registrados"
      />

      <EntityFormWindow
        description="El codigo identifica el tipo y no se puede cambiar despues del alta."
        fields={CREATE_FIELDS}
        initialValues={{ label: "", code: "", description: "" }}
        key={creating ? "type-create-open" : "type-create-closed"}
        onCancel={() => setCreating(false)}
        onSubmit={handleCreate}
        open={creating}
        submitLabel="Crear tipo"
        title="Nuevo tipo de documento"
      />

      {editing ? (
        <EntityFormWindow
          description={`El codigo ${editing.code} es inmutable.`}
          fields={EDIT_FIELDS}
          initialValues={{
            label: editing.label,
            description: editing.description ?? "",
          }}
          key={editing.public_id}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          open
          submitLabel="Guardar"
          title={`Editar ${editing.label}`}
        />
      ) : null}
    </>
  );
}
