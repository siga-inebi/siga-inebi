import { useCallback, useEffect, useMemo, useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";
import LabelOutlinedIcon from "@mui/icons-material/LabelOutlined";
import PreviewOutlinedIcon from "@mui/icons-material/PreviewOutlined";

import { PAGE_SIZE } from "@academics/academicsService.js";
import {
  documentsService,
  templateKindLabel,
  templateKindOptions,
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
import { TemplatePreviewWindow } from "./TemplatePreviewWindow.jsx";

const templateColumns = (kinds) => [
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
        label={templateKindLabel(kinds, row.kind)}
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

const createFields = (kinds) => [
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
    // Los tipos se leen del catalogo institucional, no de una lista fija
    // (RNF-MAN-001): se administran en "Tipos de documento".
    options: templateKindOptions(kinds),
    required: true,
  },
  { name: "description", label: "Descripcion (opcional)", span: "full" },
  {
    name: "content",
    label: "Contenido de la plantilla",
    type: "textarea",
    help: "Use únicamente etiquetas disponibles, por ejemplo {{student.full_name}}.",
    span: "full",
  },
];

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

  // El catalogo de tipos vive en la base de datos (RNF-MAN-001), asi que se
  // lee una vez al abrir la pantalla en vez de estar escrito aqui. Si la
  // lectura falla, la tabla sigue mostrando el codigo crudo y el formulario se
  // queda sin opciones; la pantalla no deja de funcionar por eso.
  const [kinds, setKinds] = useState([]);

  useEffect(() => {
    let active = true;
    documentsService
      .listTypes({ page_size: 100 })
      .then((payload) => {
        if (active) setKinds(payload?.results || []);
      })
      .catch(() => {
        if (active) setKinds([]);
      });
    return () => {
      active = false;
    };
  }, []);

  const columns = useMemo(() => templateColumns(kinds), [kinds]);
  const createFieldList = useMemo(() => createFields(kinds), [kinds]);
  /** El codigo es inmutable despues del alta: el backend no acepta cambiarlo. */
  const editFieldList = useMemo(
    () => createFieldList.filter((field) => field.name !== "code"),
    [createFieldList]
  );

  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);
  const [versionsFor, setVersionsFor] = useState(null);
  const [showTags, setShowTags] = useState(false);
  const [previewing, setPreviewing] = useState(null);
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
        columns={columns}
        emptyMessage="Todavia no hay plantillas registradas."
        fillHeight
        getRowKey={(template) => template.public_id}
        list={list}
        renderActions={(template) => (
          <Stack direction="row" gap={0.5} justifyContent="flex-end">
            <ActionIconButton
              label="Vista previa"
              onClick={() => setPreviewing(template)}
            >
              <PreviewOutlinedIcon fontSize="small" />
            </ActionIconButton>
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
        fields={createFieldList}
        initialValues={{
          name: "",
          code: "",
          kind: kinds[0]?.code ?? "",
          description: "",
          content: "",
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
          fields={editFieldList}
          initialValues={{
            name: editing.name,
            kind: editing.kind ?? "",
            description: editing.description ?? "",
            content: editing.content ?? "",
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
      {previewing ? (
        <TemplatePreviewWindow
          onClose={() => setPreviewing(null)}
          template={previewing}
        />
      ) : null}
    </>
  );
}
