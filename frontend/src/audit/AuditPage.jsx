import { useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";

import { auditActionLabel } from "@auth/accountLabels.js";
import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import {
  downloadBlob,
  filenameFromDisposition,
} from "@shared/utils/download.js";
import { formatDateTime } from "@shared/utils/format.js";
import { DateField } from "@ui/forms/DateField.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { DetailField } from "@ui/layout/DetailWindow.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { MutedCell } from "@ui/table/cells.jsx";

import { ACTION_PREFIX_OPTIONS, auditService } from "./auditService.js";

const EVENT_FILTERS = {
  actor_username: "",
  action_prefix: "",
  date_from: "",
  date_to: "",
};

const RETENTION_FIELDS = [
  {
    name: "category",
    label: "Categoría de datos",
    required: true,
    help: "Por ejemplo: student.health_notes, student.observations, documents.records.",
  },
  {
    name: "period_days",
    label: "Plazo de retención (días)",
    type: "number",
    min: 1,
    required: true,
  },
  {
    name: "legal_basis",
    label: "Justificación legal o institucional",
    type: "textarea",
    required: true,
  },
  {
    name: "applies_to_minors",
    label: "Aplica a datos de menores de edad",
    type: "checkbox",
  },
];

function EventDetailWindow({ event, onClose }) {
  return (
    <FloatingWindow
      onClose={onClose}
      open
      title="Asiento de bitácora"
      width={WINDOW_WIDTH.medium}
    >
      <Stack gap={2}>
        <Box
          component="dl"
          sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 2, m: 0 }}
        >
          <DetailField label="Fecha" value={formatDateTime(event.created_at)} />
          <DetailField
            label="Usuario"
            value={event.actor_label || "Sistema o anónimo"}
          />
          <DetailField label="Acción" value={auditActionLabel(event.action)} />
          <DetailField label="Código de acción" value={event.action} />
          <DetailField label="Recurso" value={event.resource} />
          <DetailField
            label="Identificador"
            value={event.resource_identifier}
          />
          <DetailField label="Dirección IP" value={event.ip_address} />
          <DetailField label="Motivo" value={event.context?.reason} />
        </Box>
        <Typography fontWeight={600} variant="subtitle2">
          Contexto
        </Typography>
        <Box
          component="pre"
          sx={{
            m: 0,
            p: 1.5,
            borderRadius: 1,
            bgcolor: "action.hover",
            fontSize: "0.75rem",
            overflowX: "auto",
          }}
        >
          {JSON.stringify(event.context ?? {}, null, 2)}
        </Box>
      </Stack>
    </FloatingWindow>
  );
}

/** AU1: consulta filtrable de la bitacora y exportacion completa. */
function AuditLog() {
  const [selected, setSelected] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const list = useServerList({
    queryKey: [...queryKeys.audit.all, "events"],
    fetchPage: auditService.events,
    defaultFilters: EVENT_FILTERS,
  });
  const { filters } = list;
  const hasFilters = Object.values(filters).some(Boolean);

  const exportCsv = async () => {
    setExporting(true);
    setExportError("");
    try {
      const { blob, headers } = await auditService.exportEvents(
        list.exportParams
      );
      downloadBlob(
        filenameFromDisposition(
          headers.get("Content-Disposition"),
          "bitacora.csv"
        ),
        blob
      );
    } catch (error) {
      setExportError(error.message);
    } finally {
      setExporting(false);
    }
  };

  const columns = [
    {
      key: "created_at",
      label: "Fecha",
      render: (row) => formatDateTime(row.created_at),
    },
    {
      key: "actor_label",
      label: "Usuario",
      render: (row) =>
        row.actor_label || <MutedCell>Sistema o anónimo</MutedCell>,
    },
    {
      key: "action",
      label: "Acción",
      render: (row) => auditActionLabel(row.action),
    },
    { key: "resource", label: "Recurso" },
    {
      key: "result",
      label: "Resultado",
      render: (row) =>
        row.context?.result === "denied"
          ? "Denegado"
          : row.context?.result
            ? "Correcto"
            : "—",
    },
  ];

  return (
    <>
      {exportError ? (
        <Alert onClose={() => setExportError("")} role="alert" severity="error">
          {exportError}
        </Alert>
      ) : null}
      <ListSection
        action={
          <Button
            disabled={exporting}
            onClick={exportCsv}
            size="small"
            startIcon={
              exporting ? (
                <CircularProgress size={14} />
              ) : (
                <FileDownloadOutlinedIcon fontSize="small" />
              )
            }
            variant="outlined"
          >
            {exporting ? "Exportando…" : "Exportar CSV"}
          </Button>
        }
        columns={columns}
        emptyMessage={
          hasFilters
            ? "Sin asientos para los filtros seleccionados."
            : "La bitácora está vacía."
        }
        fillHeight
        filters={
          <FilterBar
            onClear={
              hasFilters ? () => list.setFilters(EVENT_FILTERS) : undefined
            }
          >
            <SearchField
              debounceMs={400}
              onChange={(value) => list.setFilter("actor_username", value)}
              placeholder="Usuario"
              value={filters.actor_username}
            />
            <FilterSelect
              emptyLabel="Todas las acciones"
              label="Acción"
              minWidth={200}
              onChange={(value) => list.setFilter("action_prefix", value)}
              options={ACTION_PREFIX_OPTIONS}
              value={filters.action_prefix}
            />
            <DateField
              label="Desde"
              name="date_from"
              onChange={(event) =>
                list.setFilter("date_from", event.target.value)
              }
              value={filters.date_from}
            />
            <DateField
              label="Hasta"
              name="date_to"
              onChange={(event) =>
                list.setFilter("date_to", event.target.value)
              }
              value={filters.date_to}
            />
          </FilterBar>
        }
        getRowKey={(row) => row.public_id}
        list={list}
        onRowClick={setSelected}
        showInactiveToggle={false}
        subtitle="La exportación incluye todos los asientos del filtro y queda registrada en la bitácora."
        title="Bitácora de auditoría"
      />
      {selected ? (
        <EventDetailWindow event={selected} onClose={() => setSelected(null)} />
      ) : null}
    </>
  );
}

/** AU2: declaraciones de retencion de datos (RNF-LEG-001). */
function RetentionDeclarations() {
  const { can } = usePermissions();
  const [declaring, setDeclaring] = useState(false);
  const canRead = can(PERMISSION.AUDIT_READ);
  const list = useServerList({
    queryKey: [...queryKeys.audit.all, "retention"],
    fetchPage: auditService.retentionDeclarations,
    urlPrefix: "retention_",
    enabled: canRead,
  });

  const columns = [
    {
      key: "created_at",
      label: "Declarada",
      render: (row) => formatDateTime(row.created_at),
    },
    {
      key: "category",
      label: "Categoría",
      render: (row) => row.context?.category ?? "—",
    },
    {
      key: "period_days",
      label: "Plazo",
      render: (row) =>
        row.context?.period_days ? `${row.context.period_days} días` : "—",
    },
    {
      key: "minors",
      label: "Menores",
      render: (row) => (row.context?.applies_to_minors ? "Sí" : "No"),
    },
    {
      key: "legal_basis",
      label: "Justificación",
      render: (row) => row.context?.legal_basis ?? "—",
    },
    { key: "actor_label", label: "Declarada por" },
  ];

  return (
    <>
      <Alert severity="info" variant="outlined">
        La declaración es informativa: registra el plazo y su justificación en
        la bitácora, pero no programa ni ejecuta ninguna eliminación de datos.
      </Alert>
      {canRead ? (
        <ListSection
          action={
            can(PERMISSION.RETENTION_POLICY_DECLARE) ? (
              <Button
                onClick={() => setDeclaring(true)}
                size="small"
                variant="contained"
              >
                Declarar plazo
              </Button>
            ) : null
          }
          columns={columns}
          emptyMessage="Todavía no hay plazos de retención declarados."
          getRowKey={(row) => row.public_id}
          list={list}
          showInactiveToggle={false}
          title="Plazos de retención declarados"
        />
      ) : (
        <Button
          onClick={() => setDeclaring(true)}
          sx={{ alignSelf: "flex-start" }}
          variant="contained"
        >
          Declarar plazo
        </Button>
      )}
      {declaring ? (
        <EntityFormWindow
          description="Queda registrado en la bitácora con su autor y la fecha."
          draftKey="retention-declaration"
          fields={RETENTION_FIELDS}
          initialValues={{
            category: "",
            period_days: "",
            legal_basis: "",
            applies_to_minors: false,
          }}
          onCancel={() => setDeclaring(false)}
          onSubmit={async (values) => {
            await auditService.declareRetention(values);
            setDeclaring(false);
          }}
          open
          submitLabel="Declarar"
          title="Declarar plazo de retención"
        />
      ) : null}
    </>
  );
}

/**
 * Auditoria (docs/ux-ui.md AU1, AU2): bitacora con filtros y exportacion, y
 * declaraciones de retencion de datos.
 */
export function AuditPage() {
  const { can } = usePermissions();
  const canRead = can(PERMISSION.AUDIT_READ);
  const [tab, setTab] = useState(canRead ? "log" : "retention");

  return (
    <>
      <PageHeader
        breadcrumb="Administración"
        subtitle="Quién hizo qué y cuándo. Los asientos no se pueden modificar ni borrar."
        title="Auditoría"
      />
      <Tabs onChange={(_event, value) => setTab(value)} value={tab}>
        {canRead ? <Tab label="Bitácora" value="log" /> : null}
        <Tab label="Retención de datos" value="retention" />
      </Tabs>
      {tab === "log" && canRead ? <AuditLog /> : null}
      {tab === "retention" ? <RetentionDeclarations /> : null}
    </>
  );
}
