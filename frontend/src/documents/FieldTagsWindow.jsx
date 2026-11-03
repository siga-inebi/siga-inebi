import { useCallback, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";

import { PAGE_SIZE } from "@academics/academicsService.js";
import { documentsService } from "@documents/documentsService.js";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { CodeCell } from "@ui/table/cells.jsx";

const TAG_COLUMNS = [
  {
    key: "code",
    label: "Etiqueta",
    render: (row) => <CodeCell value={`{{${row.code}}}`} />,
  },
  { key: "label", label: "Significado", render: (row) => row.label },
  {
    key: "sensitive",
    label: "Clasificacion",
    render: (row) =>
      row.sensitive ? (
        <StatusChip label="Sensible" variant="danger" />
      ) : (
        <StatusChip label="General" variant="neutral" />
      ),
  },
];

/**
 * Catalogo cerrado de etiquetas dinamicas para plantillas (RF-PLA-002/003).
 *
 * Las sensibles quedan fuera por defecto y se piden con un interruptor explicito:
 * el requisito es que incluir un dato sensible en un documento sea una decision
 * consciente de quien arma la plantilla, no algo que aparece solo en la lista.
 */
export function FieldTagsWindow({ onClose }) {
  const [includeSensitive, setIncludeSensitive] = useState(false);

  const loadTags = useCallback(
    (params) =>
      documentsService.listFieldTags({
        ...params,
        include_sensitive: includeSensitive,
      }),
    [includeSensitive]
  );
  const list = usePaginatedList(loadTags, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  return (
    <FloatingWindow
      description="Etiquetas que una plantilla puede interpolar. El catalogo es cerrado: solo estas se sustituyen al emitir."
      footer={
        <Button onClick={onClose} variant="text">
          Cerrar
        </Button>
      }
      onClose={onClose}
      open
      title="Etiquetas dinamicas disponibles"
      width={WINDOW_WIDTH.wide}
    >
      <Stack gap={2}>
        <FormControlLabel
          control={
            <Switch
              checked={includeSensitive}
              onChange={(event) => setIncludeSensitive(event.target.checked)}
              size="small"
            />
          }
          label="Mostrar tambien etiquetas de datos sensibles"
        />

        {includeSensitive ? (
          <Alert severity="warning">
            Las etiquetas sensibles interpolan datos personales protegidos.
            Usalas solo en documentos que realmente los requieran.
          </Alert>
        ) : null}

        {list.error ? <Alert severity="error">{list.error}</Alert> : null}

        <DataTable
          columns={TAG_COLUMNS}
          emptyMessage="No hay etiquetas publicadas."
          getRowKey={(row) => row.code}
          loading={list.loading}
          pagination={list.pagination}
          rows={list.items}
        />
      </Stack>
    </FloatingWindow>
  );
}
