import { useCallback } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";

import { PAGE_SIZE } from "@academics/academicsService.js";
import {
  documentsService,
  TEMPLATE_KIND_LABEL,
} from "@documents/documentsService.js";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDateTime } from "@shared/utils/format.js";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

const VERSION_COLUMNS = [
  {
    key: "sequence",
    label: "Version",
    align: "right",
    render: (row) => `v${row.sequence}`,
  },
  { key: "name", label: "Nombre en esa version", render: (row) => row.name },
  {
    key: "kind",
    label: "Tipo",
    render: (row) => TEMPLATE_KIND_LABEL[row.kind] ?? row.kind,
  },
  {
    key: "description",
    label: "Descripcion",
    render: (row) => row.description || <MutedCell>Sin descripcion</MutedCell>,
  },
  {
    key: "created_at",
    label: "Registrada",
    render: (row) => formatDateTime(row.created_at),
  },
];

/**
 * Historial inmutable de versiones de una plantilla (RF-PLA-005).
 *
 * Solo lectura y sin accion de restaurar: el historial es evidencia de que se
 * emitio con que texto. Un boton de "volver a esta version" tendria que crear una
 * version nueva con el contenido antiguo, y eso es una decision de dominio que el
 * backend todavia no expone.
 */
export function TemplateVersionsWindow({ onClose, template }) {
  const loadVersions = useCallback(
    (params) =>
      documentsService.listTemplateVersions(template.public_id, params),
    [template.public_id]
  );
  const list = usePaginatedList(loadVersions, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  return (
    <FloatingWindow
      description={`Cada guardado de "${template.name}" quedo registrado como una version nueva. El historial no se puede modificar.`}
      footer={
        <Button onClick={onClose} variant="text">
          Cerrar
        </Button>
      }
      onClose={onClose}
      open
      title="Historial de versiones"
      width={WINDOW_WIDTH.wide}
    >
      <Stack gap={2}>
        {list.error ? <Alert severity="error">{list.error}</Alert> : null}
        <DataTable
          columns={VERSION_COLUMNS}
          emptyMessage="Esta plantilla todavia no tiene versiones registradas."
          getRowKey={(row) => row.public_id}
          loading={list.loading}
          pagination={list.pagination}
          rows={list.items}
        />
      </Stack>
    </FloatingWindow>
  );
}
