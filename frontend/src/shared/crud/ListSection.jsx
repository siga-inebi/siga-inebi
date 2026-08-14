import Alert from "@mui/material/Alert";
import FormControlLabel from "@mui/material/FormControlLabel";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";

import { DataTable } from "@ui/table/DataTable.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";

/**
 * Seccion de listado de catalogo: encabezado, interruptor de inactivos, errores
 * y tabla paginada.
 *
 * Existe para que las cuatro pantallas de catalogo (sedes, niveles, cursos,
 * personas) declaren solo *que* muestran — columnas y acciones — y no repitan
 * cuatro veces la misma composicion de card, switch, alertas y paginador.
 *
 * @param {object}   props
 * @param {object}   props.list     Resultado de `usePaginatedList`.
 * @param {Array}    props.columns       Columnas de `DataTable` ({key,label,align,render}).
 * @param {Function} props.getRowKey
 * @param {string}   props.title
 * @param {string}  [props.subtitle]
 * @param {ReactNode}[props.action]      Accion primaria de la seccion.
 * @param {Function}[props.renderActions] Si viene, agrega la columna "Acciones".
 * @param {string}  [props.emptyMessage]
 * @param {string}  [props.actionError]  Error de una accion de fila (baja, etc).
 * @param {boolean} [props.showInactiveToggle=true]
 * @param {boolean} [props.fillHeight]
 */
export function ListSection({
  action,
  actionError,
  list,
  columns,
  emptyMessage = "No hay registros para mostrar.",
  fillHeight = false,
  getRowKey,
  renderActions,
  showInactiveToggle = true,
  subtitle,
  title,
}) {
  const allColumns = renderActions
    ? [
        ...columns,
        {
          key: "acciones",
          label: "Acciones",
          align: "right",
          render: renderActions,
        },
      ]
    : columns;

  return (
    <SectionCard action={action} fillHeight={fillHeight} subtitle={subtitle} title={title}>
      {showInactiveToggle ? (
        <Stack
          direction="row"
          sx={{
            px: { xs: 1.5, md: 2 },
            py: 1,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <FormControlLabel
            control={
              <Switch
                checked={list.includeInactive}
                onChange={(event) => list.setIncludeInactive(event.target.checked)}
                size="small"
              />
            }
            label="Mostrar desactivados"
          />
        </Stack>
      ) : null}

      {list.error || actionError ? (
        <Stack gap={1} sx={{ px: { xs: 1.5, md: 2 }, pt: 1.5 }}>
          {list.error ? (
            <Alert role="alert" severity="error" variant="outlined">
              {list.error}
            </Alert>
          ) : null}
          {actionError ? (
            <Alert role="alert" severity="error" variant="outlined">
              {actionError}
            </Alert>
          ) : null}
        </Stack>
      ) : null}

      <SectionTableArea>
        <DataTable
          columns={allColumns}
          emptyMessage={emptyMessage}
          fillHeight={fillHeight}
          getRowKey={getRowKey}
          loading={list.loading}
          pagination={list.pagination}
          rows={list.items}
        />
      </SectionTableArea>
    </SectionCard>
  );
}
