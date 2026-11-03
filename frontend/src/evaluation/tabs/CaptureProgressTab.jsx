import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import LinearProgress from "@mui/material/LinearProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { evaluationService } from "@evaluation/evaluationService.js";
import {
  defaultUnit,
  unitLabel,
  useCycleUnits,
  useUrlParams,
} from "@evaluation/evaluationData.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { formatPercent } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { SectionCard, SectionTableArea } from "@ui/layout/SectionCard.jsx";
import { DataTable } from "@ui/table/DataTable.jsx";

function ProgressBar({ label, value }) {
  return (
    <Stack alignItems="center" direction="row" gap={1} sx={{ minWidth: 160 }}>
      <Box sx={{ flex: 1 }}>
        <LinearProgress
          aria-label={label}
          value={Math.min(100, Math.max(0, value ?? 0))}
          variant="determinate"
        />
      </Box>
      <Typography sx={{ minWidth: 48, textAlign: "right" }} variant="body2">
        {value == null ? "—" : formatPercent(value)}
      </Typography>
    </Stack>
  );
}

/**
 * Avance de captura de una unidad (RF-CAL-008, docs/ux-ui.md V3): cuánto
 * falta por calificar en cada sección y subárea. Quien configura ve todo; un
 * docente, solo sus asignaciones. Cada fila abre su planilla.
 */
export function CaptureProgressTab({ cycle, goTo }) {
  const cycleId = cycle.public_id;
  const [params, setParams] = useUrlParams();
  const units = useCycleUnits(cycleId);
  const unitList = units.data ?? [];
  const unit =
    unitList.find((item) => item.public_id === params.get("unidad")) ??
    defaultUnit(unitList);

  const progress = useQuery({
    queryKey: queryKeys.evaluation(cycleId, "progress", unit?.public_id),
    queryFn: () =>
      evaluationService.getCaptureProgress(cycleId, unit.public_id),
    enabled: Boolean(unit),
  });
  const report = progress.data;
  const rows = report?.rows ?? [];

  return (
    <Stack gap={2}>
      <FilterBar>
        <FilterSelect
          label="Unidad"
          loading={units.isPending}
          minWidth={220}
          onChange={(value) => setParams({ unidad: value })}
          options={unitList.map((item) => ({
            value: item.public_id,
            label: unitLabel(item),
          }))}
          value={unit?.public_id ?? ""}
        />
      </FilterBar>

      {units.isSuccess && unitList.length === 0 ? (
        <Typography color="text.secondary" variant="body2">
          Este ciclo no tiene unidades de evaluación.
        </Typography>
      ) : null}
      {progress.error ? (
        <Alert severity="error">{progress.error.message}</Alert>
      ) : null}

      {report ? (
        <SectionCard
          action={
            <StatusChip
              label={report.window_open ? "Captura abierta" : "Captura cerrada"}
              variant={report.window_open ? "success" : "neutral"}
            />
          }
          subtitle={`${rows.reduce((sum, row) => sum + row.students_pending, 0)} notas pendientes en ${rows.length} combinaciones de sección y subárea.`}
          title={`Avance de «${report.unit_name}»`}
        >
          <Stack gap={2} sx={{ p: { xs: 1.5, md: 2 } }}>
            <Box>
              <Typography sx={{ fontWeight: 600, mb: 0.5 }} variant="body2">
                Avance general
              </Typography>
              <ProgressBar
                label="Avance general"
                value={report.overall_progress_pct}
              />
            </Box>
            <SectionTableArea>
              <DataTable
                columns={[
                  {
                    key: "section",
                    label: "Sección",
                    render: (row) => row.section.name,
                  },
                  {
                    key: "subject",
                    label: "Subárea",
                    render: (row) => row.subject.name,
                  },
                  {
                    key: "teacher",
                    label: "Docente",
                    render: (row) => row.teacher?.name ?? "Sin docente",
                  },
                  {
                    key: "progress",
                    label: "Avance",
                    render: (row) => (
                      <ProgressBar
                        label={`Avance de ${row.section.name}, ${row.subject.name}`}
                        value={row.progress_pct}
                      />
                    ),
                  },
                  {
                    key: "pending",
                    label: "Pendientes",
                    align: "right",
                    render: (row) =>
                      `${row.students_pending} de ${row.students_total}`,
                  },
                  {
                    key: "open",
                    label: "Acciones",
                    align: "right",
                    render: (row) => (
                      <Button
                        aria-label={`Abrir planilla de ${row.section.name}, ${row.subject.name}`}
                        onClick={() =>
                          goTo("planilla", {
                            unidad: unit.public_id,
                            seccion: row.section.public_id,
                            subarea: row.subject.public_id,
                          })
                        }
                        size="small"
                      >
                        Abrir planilla
                      </Button>
                    ),
                  },
                ]}
                emptyMessage="No hay secciones con subáreas que calificar en esta unidad."
                getRowKey={(row) =>
                  `${row.section.public_id}-${row.subject.public_id}`
                }
                rows={rows}
              />
            </SectionTableArea>
          </Stack>
        </SectionCard>
      ) : unit && progress.isPending ? (
        <Typography role="status">Cargando avance…</Typography>
      ) : null}
    </Stack>
  );
}
