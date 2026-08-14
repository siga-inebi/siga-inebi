import { useCallback, useEffect, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import RuleOutlinedIcon from "@mui/icons-material/RuleOutlined";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";

import { PAGE_SIZE } from "@academics/academicsService.js";
import {
  ALERT_LABEL,
  ALERT_TYPE_OPTIONS,
  ALERT_VARIANT,
  reportingService,
} from "@reporting/reportingService.js";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDate, formatDateTime } from "@shared/utils/format.js";
import { ConfirmActionButton } from "@ui/buttons/ConfirmActionButton.jsx";
import { StatCard } from "@ui/display/StatCard.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { FilterSelect } from "@ui/filters/FilterSelect.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { CodeCell, MutedCell } from "@ui/table/cells.jsx";

import { AbsenceThresholdsWindow } from "./AbsenceThresholdsWindow.jsx";
import { AlertEvaluationWindow } from "./AlertEvaluationWindow.jsx";

const ALL_TYPES = "";
const PENDING = "pending";
const ACKNOWLEDGED = "acknowledged";
const ALL_STATES = "";

const STATE_OPTIONS = [
  { value: PENDING, label: "Sin atender" },
  { value: ACKNOWLEDGED, label: "Atendidas" },
  { value: ALL_STATES, label: "Todas" },
];

const TYPE_FILTER_OPTIONS = [{ value: ALL_TYPES, label: "Todos los tipos" }, ...ALERT_TYPE_OPTIONS];

/**
 * Conteo total de alertas que cumplen un filtro.
 *
 * Consulta la primera pagina solo para leer `count`: el endpoint pagina, asi que
 * contar en el cliente sobre la pagina visible daria un numero equivocado en
 * cuanto haya mas de una pagina.
 */
function useAlertCount(params, token) {
  const [count, setCount] = useState(null);
  // Los filtros se serializan para poder usarlos como dependencia estable: un
  // objeto literal seria una referencia nueva en cada render y recargaria en bucle.
  const key = JSON.stringify(params);

  useEffect(() => {
    let active = true;
    reportingService
      .listAlerts(JSON.parse(key))
      .then((page) => {
        if (active) setCount(page?.count ?? 0);
      })
      .catch(() => {
        // Sin permiso o sin datos: el indicador queda en blanco, la tabla ya
        // muestra el error real.
        if (active) setCount(null);
      });
    return () => {
      active = false;
    };
    // `token` fuerza el recalculo tras atender una alerta, sin viajar como
    // parametro de la peticion.
  }, [key, token]);

  return count;
}

export function AlertsPage() {
  const [typeFilter, setTypeFilter] = useState(ALL_TYPES);
  const [stateFilter, setStateFilter] = useState(PENDING);
  const [showThresholds, setShowThresholds] = useState(false);
  const [showEvaluation, setShowEvaluation] = useState(false);
  const [actionError, setActionError] = useState("");
  const [countsToken, setCountsToken] = useState(0);

  // Los filtros viajan al backend porque el endpoint los soporta
  // (`alert_type`, `acknowledged`). Filtrar en memoria mostraria solo lo que
  // cupo en la pagina actual y ademas mentiria en los totales.
  const loadAlerts = useCallback(
    (params) =>
      reportingService.listAlerts({
        ...params,
        alert_type: typeFilter || undefined,
        acknowledged:
          stateFilter === PENDING ? false : stateFilter === ACKNOWLEDGED ? true : undefined,
      }),
    [stateFilter, typeFilter]
  );

  const list = usePaginatedList(loadAlerts, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  const pendingCount = useAlertCount({ acknowledged: false }, countsToken);
  const totalCount = useAlertCount({}, countsToken);
  const frequentCount = useAlertCount({ alert_type: "frecuencia_ausencias" }, countsToken);

  const refreshAll = () => {
    list.refresh();
    setCountsToken((value) => value + 1);
  };

  const handleAcknowledge = async (alert) => {
    setActionError("");
    try {
      await reportingService.acknowledge(alert.public_id);
      refreshAll();
    } catch (requestError) {
      setActionError(requestError.message);
      throw requestError;
    }
  };

  const columns = [
    {
      key: "alert_type",
      label: "Alerta",
      render: (row) => (
        <StatusChip
          label={ALERT_LABEL[row.alert_type] ?? row.alert_type}
          variant={ALERT_VARIANT[row.alert_type] ?? "warning"}
        />
      ),
    },
    {
      key: "student_id",
      label: "Estudiante",
      render: (row) => <CodeCell value={row.student_id} />,
    },
    { key: "event_date", label: "Fecha", render: (row) => formatDate(row.event_date) },
    {
      key: "section_id",
      label: "Seccion",
      render: (row) =>
        row.section_id ? <CodeCell value={row.section_id} /> : <MutedCell>Sin seccion</MutedCell>,
    },
    {
      key: "acknowledged",
      label: "Atencion",
      render: (row) =>
        row.acknowledged_at ? (
          <Stack gap={0.25}>
            <StatusChip label="Atendida" variant="success" />
            <MutedCell>
              {row.acknowledged_by_username || "sin usuario"} ·{" "}
              {formatDateTime(row.acknowledged_at)}
            </MutedCell>
          </Stack>
        ) : (
          <StatusChip label="Sin atender" variant="warning" />
        ),
    },
  ];

  return (
    <>
      <PageHeader
        action={
          <Stack direction="row" gap={1}>
            <Button
              onClick={() => setShowThresholds(true)}
              startIcon={<TuneOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              Umbrales de ausencia
            </Button>
            <Button
              onClick={() => setShowEvaluation(true)}
              startIcon={<RuleOutlinedIcon fontSize="small" />}
              variant="contained"
            >
              Recalcular jornada
            </Button>
          </Stack>
        }
        breadcrumb="Reportes y control"
        subtitle="Alertas institucionales de asistencia. Atender una alerta la deja registrada con tu usuario; el hecho que la origino se conserva."
        title="Alertas"
      />

      <Grid container spacing={2} sx={{ mb: 1 }}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard
            label="Sin atender"
            loading={pendingCount == null}
            value={pendingCount ?? "—"}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard label="Total registradas" loading={totalCount == null} value={totalCount ?? "—"} />
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <StatCard
            hint="Superan el umbral configurado"
            label="Frecuencia de ausencias"
            loading={frequentCount == null}
            value={frequentCount ?? "—"}
          />
        </Grid>
      </Grid>

      <ListSection
        actionError={actionError}
        columns={columns}
        emptyMessage={
          stateFilter === PENDING
            ? "No hay alertas sin atender."
            : "Sin datos para los filtros seleccionados."
        }
        fillHeight
        filters={
          <FilterBar
            onClear={
              typeFilter || stateFilter !== PENDING
                ? () => {
                    setTypeFilter(ALL_TYPES);
                    setStateFilter(PENDING);
                  }
                : undefined
            }
          >
            <FilterSelect
              label="Tipo de alerta"
              minWidth={230}
              onChange={setTypeFilter}
              options={TYPE_FILTER_OPTIONS}
              value={typeFilter}
            />
            <FilterSelect
              label="Atencion"
              minWidth={160}
              onChange={setStateFilter}
              options={STATE_OPTIONS}
              value={stateFilter}
            />
          </FilterBar>
        }
        getRowKey={(row) => row.public_id}
        list={list}
        renderActions={(row) =>
          row.acknowledged_at ? null : (
            <ConfirmActionButton
              color="primary"
              confirmLabel="Si, marcar atendida"
              label="Atender"
              onConfirm={() => handleAcknowledge(row)}
              question="La alerta quedara registrada como atendida por tu usuario. El hecho que la origino no se modifica."
              title="Marcar alerta como atendida"
            />
          )
        }
        showInactiveToggle={false}
        subtitle="Tablero de atencion"
        title="Alertas registradas"
      />

      {showThresholds ? (
        <AbsenceThresholdsWindow onClose={() => setShowThresholds(false)} />
      ) : null}

      {showEvaluation ? (
        <AlertEvaluationWindow
          onClose={() => setShowEvaluation(false)}
          onEvaluated={refreshAll}
        />
      ) : null}
    </>
  );
}
