import { useCallback, useEffect, useMemo, useState } from "react";

import Alert from "@mui/material/Alert";
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
  templateIssuanceUseLabel,
  TEMPLATE_KIND_VARIANT,
} from "@documents/documentsService.js";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { ConfirmActionButton } from "@ui/buttons/ConfirmActionButton.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { ActiveCell, CodeCell, MutedCell } from "@ui/table/cells.jsx";

import { TemplateFormWindow } from "./TemplateFormWindow.jsx";

import { FieldTagsWindow } from "./FieldTagsWindow.jsx";
import { TemplateVersionsWindow } from "./TemplateVersionsWindow.jsx";
import { TemplatePreviewWindow } from "./TemplatePreviewWindow.jsx";

const templateColumns = (kinds, uses) => [
  {
    key: "issuance_use",
    label: "Se usa para",
    render: (row) =>
      uses.find((use) => use.code === row.issuance_use)?.label ??
      templateIssuanceUseLabel(row.issuance_use),
  },
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

  const [uses, setUses] = useState([]);
  const [usesError, setUsesError] = useState("");
  const loadUses = useCallback(async () => {
    try {
      setUses(await documentsService.listTemplateIssuanceUses());
      setUsesError("");
    } catch (error) {
      setUsesError(error.message);
    }
  }, []);
  useEffect(() => {
    loadUses();
  }, [loadUses]);
  const columns = useMemo(() => templateColumns(kinds, uses), [kinds, uses]);

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
    loadUses();
  };

  const handleUpdate = async (payload) => {
    await documentsService.updateTemplate(editing.public_id, payload);
    setEditing(null);
    list.refresh();
    loadUses();
  };

  const handleDeactivate = async (template) => {
    setActionError("");
    try {
      await documentsService.deactivateTemplate(template.public_id);
      list.refresh();
      loadUses();
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

      {usesError ? (
        <Alert
          severity="error"
          action={<Button onClick={loadUses}>Reintentar</Button>}
        >
          {usesError}
        </Alert>
      ) : (
        uses
          .filter((use) => use.uses_fallback)
          .map((use) => (
            <Alert key={use.code} severity="warning">
              {use.label} usa el texto por defecto
              {use.active_template
                ? ": su plantilla activa no tiene contenido publicado."
                : ": no hay plantilla activa para este uso."}
            </Alert>
          ))
      )}

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

      {creating ? (
        <TemplateFormWindow
          kinds={kinds}
          onCancel={() => setCreating(false)}
          onSubmit={handleCreate}
        />
      ) : null}
      {editing ? (
        <TemplateFormWindow
          kinds={kinds}
          template={editing}
          onCancel={() => setEditing(null)}
          onSubmit={handleUpdate}
        />
      ) : null}

      {versionsFor ? (
        <TemplateVersionsWindow
          onRestored={list.refresh}
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
