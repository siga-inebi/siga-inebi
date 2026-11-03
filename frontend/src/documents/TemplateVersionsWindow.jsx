import { useCallback, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Checkbox from "@mui/material/Checkbox";
import Grid from "@mui/material/Grid";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { PAGE_SIZE } from "@academics/academicsService.js";
import {
  documentsService,
  templateIssuanceUseLabel,
} from "@documents/documentsService.js";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDateTime } from "@shared/utils/format.js";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

const VERSION_COLUMNS = [
  {
    key: "issuance_use",
    label: "Se usaba para",
    render: (row) => templateIssuanceUseLabel(row.issuance_use),
  },
  {
    key: "sequence",
    label: "Version",
    align: "right",
    render: (row) => `v${row.sequence}`,
  },
  { key: "name", label: "Nombre en esa version", render: (row) => row.name },
  {
    // La version guarda el CODIGO del tipo tal como estaba al emitirla, no su
    // nombre visible (RF-PLA-005). Traducirlo con el catalogo de hoy mostraria
    // una etiqueta que quiza no existia entonces, asi que se muestra el codigo.
    key: "kind",
    label: "Tipo",
    render: (row) => row.kind,
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
function readableContent(version) {
  return typeof version.content === "string"
    ? version.content
    : version.content?.content
        ?.map((block) => block.content?.map((node) => node.text).join(""))
        .join("\n");
}

export function TemplateVersionsWindow({ onClose, onRestored, template }) {
  const [selected, setSelected] = useState([]);
  const [restoring, setRestoring] = useState(false);
  const [actionError, setActionError] = useState("");
  const loadVersions = useCallback(
    (params) =>
      documentsService.listTemplateVersions(template.public_id, params),
    [template.public_id]
  );
  const list = usePaginatedList(loadVersions, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });
  const columns = [
    {
      key: "compare",
      label: "Comparar",
      render: (row) => (
        <Checkbox
          inputProps={{ "aria-label": `Comparar versión ${row.sequence}` }}
          checked={selected.some((item) => item.public_id === row.public_id)}
          disabled={
            !selected.some((item) => item.public_id === row.public_id) &&
            selected.length === 2
          }
          onChange={(event) =>
            setSelected((current) =>
              event.target.checked
                ? [...current, row]
                : current.filter((item) => item.public_id !== row.public_id)
            )
          }
        />
      ),
    },
    ...VERSION_COLUMNS,
    {
      key: "restore",
      label: "Acción",
      render: (row) => (
        <Button
          size="small"
          disabled={restoring || row.sequence === list.items[0]?.sequence}
          onClick={async () => {
            if (
              !window.confirm(
                `Restaurar la versión ${row.sequence} como una versión nueva?`
              )
            )
              return;
            setRestoring(true);
            setActionError("");
            try {
              await documentsService.restoreTemplateVersion(
                template.public_id,
                row.public_id
              );
              list.refresh();
              onRestored?.();
            } catch (requestError) {
              setActionError(requestError.message);
            } finally {
              setRestoring(false);
            }
          }}
        >
          Restaurar
        </Button>
      ),
    },
  ];

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
        {list.error || actionError ? (
          <Alert severity="error">{list.error || actionError}</Alert>
        ) : null}
        {selected.length === 2 ? (
          <Grid container spacing={2}>
            {selected.map((version) => (
              <Grid size={{ xs: 12, md: 6 }} key={version.public_id}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                  <Typography variant="h6">
                    Versión {version.sequence}
                  </Typography>
                  <Typography
                    component="pre"
                    sx={{ whiteSpace: "pre-wrap", fontFamily: "inherit" }}
                  >
                    {readableContent(version)}
                  </Typography>
                  <Typography variant="caption">
                    {version.page_size.toUpperCase()} · {version.orientation} ·{" "}
                    {version.footer_text || "Sin pie"}
                  </Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>
        ) : (
          <Alert severity="info">
            Seleccione dos versiones para compararlas lado a lado.
          </Alert>
        )}
        <DataTable
          columns={columns}
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
