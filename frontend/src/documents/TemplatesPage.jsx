import { useCallback, useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";
import LabelOutlinedIcon from "@mui/icons-material/LabelOutlined";

import { PAGE_SIZE } from "@academics/academicsService.js";
import {
  documentsService,
  TEMPLATE_KIND_LABEL,
  TEMPLATE_KIND_OPTIONS,
  TEMPLATE_KIND_VARIANT,
} from "@documents/documentsService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { ConfirmActionButton } from "@ui/buttons/ConfirmActionButton.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { ActiveCell, CodeCell, MutedCell } from "@ui/table/cells.jsx";

import { FieldTagsWindow } from "./FieldTagsWindow.jsx";
import { TemplateVersionsWindow } from "./TemplateVersionsWindow.jsx";

const TEMPLATE_COLUMNS = [
  { key: "name", label: "Plantilla", render: (row) => row.name },
  {
    key: "code",
    label: "Codigo",
    render: (row) => <CodeCell value={row.code} />,
  },
  {
    key: "kind",
    label: "Tipo",
    render: (row) => (
      <StatusChip
        label={TEMPLATE_KIND_LABEL[row.kind] ?? row.kind}
        variant={TEMPLATE_KIND_VARIANT[row.kind] ?? "neutral"}
      />
    ),
  },
  {
    key: "description",
    label: "Descripcion",
    render: (row) => row.description || <MutedCell>Sin descripcion</MutedCell>,
  },
  {
    key: "header",
    label: "Encabezado",
    render: (row) =>
      row.header ? (
        <StatusChip label="Institucional" variant="success" />
      ) : (
        <MutedCell>Sin encabezado</MutedCell>
      ),
  },
  {
    key: "is_active",
    label: "Estado",
    render: (row) => <ActiveCell active={row.is_active} />,
  },
];

const CREATE_FIELDS = [
  {
    name: "name",
    label: "Nombre",
    required: true,
    placeholder: "Ejemplo: Constancia de inscripcion",
  },
  {
    name: "code",
    label: "Codigo",
    required: true,
    placeholder: "Ejemplo: CONST-INS",
  },
  {
    name: "kind",
    label: "Tipo",
    type: "select",
    options: TEMPLATE_KIND_OPTIONS,
    required: true,
  },
  { name: "description", label: "Descripcion (opcional)", span: "full" },
];

/** El codigo es inmutable despues del alta: el backend no acepta cambiarlo. */
const EDIT_FIELDS = CREATE_FIELDS.filter((field) => field.name !== "code");

/**
 * Catalogo de plantillas documentales.
 *
 * Cada guardado genera una version nueva e inmutable en el backend (RF-PLA-005),
 * asi que "editar" aqui no reescribe la plantilla: agrega una version. La ventana
 * de historial es la que hace visible ese comportamiento, por eso vive junto a la
 * accion de editar y no en otra pantalla.
 */
export function TemplatesPage() {
  const loadTemplates = useCallback(
    (params) => documentsService.listTemplates(params),
    []
  );
  const list = usePaginatedList(loadTemplates, { pageSize: PAGE_SIZE });

  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);
  const [versionsFor, setVersionsFor] = useState(null);
  const [showTags, setShowTags] = useState(false);
  const [actionError, setActionError] = useState("");

  const handleCreate = async (payload) => {
    await documentsService.createTemplate(payload);
    setCreating(false);
    list.refresh();
  };

  const handleUpdate = async (payload) => {
    await documentsService.updateTemplate(editing.public_id, payload);
    setEditing(null);
    list.refresh();
  };

  const handleDeactivate = async (template) => {
    setActionError("");
    try {
      await documentsService.deactivateTemplate(template.public_id);
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
          <Stack direction="row" gap={1}>
            <Button
              onClick={() => setShowTags(true)}
              startIcon={<LabelOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              Etiquetas disponibles
            </Button>
            <Button
              onClick={() => setCreating(true)}
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Nueva plantilla
            </Button>
          </Stack>
        }
        breadcrumb="Documentos"
        subtitle="Plantillas de constancias y reportes. Cada cambio guardado queda como una version nueva e inmutable; el encabezado institucional es obligatorio al emitir."
        title="Plantillas documentales"
      />

      <ListSection
        actionError={actionError}
        columns={TEMPLATE_COLUMNS}
        emptyMessage="Todavia no hay plantillas registradas."
        fillHeight
        getRowKey={(template) => template.public_id}
        list={list}
        renderActions={(template) => (
          <Stack direction="row" gap={0.5} justifyContent="flex-end">
            <ActionIconButton
              label="Historial de versiones"
              onClick={() => setVersionsFor(template)}
            >
              <HistoryOutlinedIcon fontSize="small" />
            </ActionIconButton>
            <ActionIconButton
              label="Editar"
              onClick={() => setEditing(template)}
            >
              <EditOutlinedIcon fontSize="small" />
            </ActionIconButton>
            {template.is_active ? (
              <ConfirmActionButton
                confirmLabel="Si, desactivar"
                label="Desactivar"
                onConfirm={() => handleDeactivate(template)}
                question={`Se desactivara "${template.name}". Las versiones ya emitidas se conservan; la plantilla deja de estar disponible para documentos nuevos.`}
                title="Desactivar plantilla"
              />
            ) : null}
          </Stack>
        )}
        subtitle="Catalogo institucional"
        title="Plantillas registradas"
      />

      <EntityFormWindow
        description="El codigo identifica la plantilla y no se puede cambiar despues del alta."
        fields={CREATE_FIELDS}
        initialValues={{
          name: "",
          code: "",
          kind: "certificate",
          description: "",
        }}
        key={creating ? "template-create-open" : "template-create-closed"}
        onCancel={() => setCreating(false)}
        onSubmit={handleCreate}
        open={creating}
        submitLabel="Crear plantilla"
        title="Nueva plantilla documental"
      />

      {editing ? (
        <EntityFormWindow
          description={`Guardar genera una version nueva de la plantilla. El codigo ${editing.code} es inmutable.`}
          fields={EDIT_FIELDS}
          initialValues={{
            name: editing.name,
            kind: editing.kind ?? "other",
            description: editing.description ?? "",
          }}
          key={editing.public_id}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
          open
          submitLabel="Guardar version"
          title={`Editar ${editing.name}`}
        />
      ) : null}

      {versionsFor ? (
        <TemplateVersionsWindow
          key={versionsFor.public_id}
          onClose={() => setVersionsFor(null)}
          template={versionsFor}
        />
      ) : null}

      {showTags ? <FieldTagsWindow onClose={() => setShowTags(false)} /> : null}
    </>
  );
}
