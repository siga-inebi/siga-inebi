import Alert from "@mui/material/Alert";
import Grid from "@mui/material/Grid";
import LinearProgress from "@mui/material/LinearProgress";

import { documentsService } from "@documents/documentsService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { useResourceQuery } from "@shared/api/useResourceQuery.js";
import { StatCard } from "@ui/display/StatCard.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";

function formatBytes(value = 0) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 ** 2) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 ** 3) return `${(value / 1024 ** 2).toFixed(1)} MB`;
  return `${(value / 1024 ** 3).toFixed(2)} GB`;
}

export function DocumentStoragePage() {
  const { data, error, loading } = useResourceQuery(
    queryKeys.documents.storage(),
    () => documentsService.storageConsumption(),
    { defaultData: null }
  );
  const percent = Math.min(100, data?.threshold_utilization_percent ?? 0);

  return (
    <>
      <PageHeader
        breadcrumb="Documentos y control"
        subtitle="Capacidad utilizada por los archivos de expedientes y proyección para el siguiente ciclo."
        title="Almacenamiento documental"
      />
      {error ? <Alert severity="error">{error.message}</Alert> : null}
      {data?.warning_active ? (
        <Alert severity="warning" sx={{ mb: 2 }}>
          El consumo alcanzó el umbral operativo. Revise la capacidad antes de
          recibir nuevos archivos.
        </Alert>
      ) : null}
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard
            label="Espacio utilizado"
            loading={loading}
            value={formatBytes(data?.total_bytes)}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard
            label="Archivos registrados"
            loading={loading}
            value={data?.file_count ?? "—"}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard
            label="Archivos conservados"
            loading={loading}
            value={data?.retained_count ?? "—"}
          />
        </Grid>
      </Grid>
      <SectionCard
        subtitle={`Umbral ${formatBytes(data?.warning_threshold_bytes)} · Proyección ${formatBytes(data?.projected_total_bytes)}`}
        title="Uso por tipo de archivo"
      >
        <LinearProgress
          aria-label="Uso del umbral de almacenamiento"
          sx={{ m: 2 }}
          value={percent}
          variant="determinate"
        />
        <SectionTableArea>
          <DataTable
            columns={[
              {
                key: "content_type",
                label: "Tipo",
                render: (row) => row.content_type || "Sin tipo",
              },
              { key: "count", label: "Archivos", align: "right" },
              {
                key: "size",
                label: "Espacio",
                align: "right",
                render: (row) => formatBytes(row.size),
              },
            ]}
            emptyMessage="No hay archivos almacenados."
            getRowKey={(row) => row.content_type || "unknown"}
            loading={loading}
            rows={data?.by_content_type ?? []}
          />
        </SectionTableArea>
      </SectionCard>
    </>
  );
}

export default DocumentStoragePage;
