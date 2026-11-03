import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import AddIcon from "@mui/icons-material/Add";

import {
  CYCLE_STATUS,
  CYCLE_STATUS_LABEL,
  CYCLE_STATUS_VARIANT,
  cyclesService,
} from "@cycles/cyclesService.js";
import { PERMISSION } from "@auth/permissions.js";
import { usePermissions } from "@auth/usePermissions.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { useServerList } from "@shared/crud/useServerList.js";
import { formatDate } from "@shared/utils/format.js";
import { RowActionsMenu } from "@ui/buttons/RowActionsMenu.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { TextLink } from "@ui/display/TextLink.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

import { CycleFormWindow } from "./CycleFormWindow.jsx";
import { cyclePath, nextCycleYear } from "./cyclePresentation.js";
import { useCycleActions } from "./useCycleActions.jsx";

const COLUMNS = [
  { key: "year", label: "Año", align: "right", render: (row) => row.year },
  {
    key: "name",
    label: "Ciclo",
    render: (row) => (
      <TextLink
        onClick={(event) => event.stopPropagation()}
        to={cyclePath(row)}
      >
        {row.name}
      </TextLink>
    ),
  },
  {
    key: "range",
    label: "Vigencia",
    render: (row) =>
      `${formatDate(row.starts_on)} — ${formatDate(row.ends_on)}`,
  },
  {
    key: "description",
    label: "Descripción",
    render: (row) => row.description || <MutedCell>Sin descripción</MutedCell>,
  },
  {
    key: "status",
    label: "Estado",
    render: (row) => (
      <StatusChip
        label={CYCLE_STATUS_LABEL[row.status] ?? row.status}
        variant={CYCLE_STATUS_VARIANT[row.status] ?? "neutral"}
      />
    ),
  },
];

/**
 * El otro ciclo activo (D1) y la preparacion del ciclo activo (D6), con a lo
 * sumo una consulta a `readiness/`: la del ciclo activo de la pagina si esta, o
 * la de un borrador, que informa cual es el activo aunque este en otra pagina.
 */
function useListContext(cycles) {
  const activeOnPage = cycles.find(
    (cycle) => cycle.status === CYCLE_STATUS.active
  );
  const probe =
    activeOnPage ?? cycles.find((cycle) => cycle.status === CYCLE_STATUS.draft);
  const readiness = useQuery({
    queryKey: queryKeys.academics.readiness(probe?.public_id),
    queryFn: () => cyclesService.readiness(probe.public_id),
    enabled: Boolean(probe),
  });

  const activeCycle = activeOnPage
    ? { public_id: activeOnPage.public_id, name: activeOnPage.name }
    : (readiness.data?.active_cycle ?? null);

  return {
    activeCycle,
    contextFor: (cycle) => ({
      activeCycle,
      readiness:
        cycle.public_id === probe?.public_id ? (readiness.data ?? null) : null,
    }),
  };
}

/**
 * Ciclos escolares (docs/ux-ui.md 2.1): registro, activación, cierre, clonado,
 * edición del borrador, volver a borrador y reabrir.
 *
 * El listado pagina en el servidor y deja la página en la URL. Cada fila abre
 * el detalle del ciclo (`/app/ciclos/:id`), que es también el tablero de
 * preparación del borrador (C9). Las acciones van en el menú de la fila y se
 * deshabilitan, con el motivo, cuando el backend las rechazaría (D1, D2, D6).
 */
export function CyclesPage() {
  const navigate = useNavigate();
  const { can } = usePermissions();
  const [creating, setCreating] = useState(false);

  const list = useServerList({
    queryKey: queryKeys.academics.list("cycles"),
    fetchPage: cyclesService.list,
  });
  const { activeCycle, contextFor } = useListContext(list.items);

  const openCycle = (cycle) => navigate(cyclePath(cycle));
  const { actionsFor, dialogs } = useCycleActions({
    onChanged: list.refresh,
    onCloned: openCycle,
    onView: openCycle,
  });

  const hasDrafts = list.items.some(
    (cycle) => cycle.status === CYCLE_STATUS.draft
  );

  return (
    <>
      <PageHeader
        action={
          can(PERMISSION.SCOPE_ASSIGN) ? (
            <Button
              onClick={() => setCreating(true)}
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Nuevo ciclo
            </Button>
          ) : null
        }
        breadcrumb="Estructura académica"
        subtitle="Un ciclo nace en borrador, se prepara (secciones, plan de estudios, asignaciones y horarios) y se activa. Solo puede haber un ciclo activo: para activar otro, cierre antes el vigente."
        title="Ciclo escolar"
      />

      {activeCycle && hasDrafts ? (
        <Alert severity="info" sx={{ mb: 2 }}>
          El ciclo activo es «{activeCycle.name}». Para activar un borrador,
          cierre primero ese ciclo.{" "}
          <TextLink to={cyclePath(activeCycle)}>
            Ver «{activeCycle.name}»
          </TextLink>
        </Alert>
      ) : null}

      {dialogs}

      <ListSection
        columns={COLUMNS}
        emptyMessage="Todavía no hay ciclos registrados."
        fillHeight
        getRowKey={(cycle) => cycle.public_id}
        list={list}
        onRowClick={openCycle}
        renderActions={(cycle) => (
          <RowActionsMenu
            actions={actionsFor(cycle, contextFor(cycle))}
            label={cycle.name}
          />
        )}
        showInactiveToggle={false}
        subtitle="Clic en una fila para abrir el ciclo y su preparación."
        title="Ciclos registrados"
      />

      {creating ? (
        <CycleFormWindow
          description="Elija el año: el nombre y la vigencia salen del calendario escolar. El ciclo nace en borrador y se vuelve vigente cuando se activa."
          initialYear={nextCycleYear()}
          onCancel={() => setCreating(false)}
          onSubmit={async (payload) => {
            const created = await cyclesService.create(payload);
            setCreating(false);
            list.refresh();
            if (created?.public_id) openCycle(created);
          }}
          submitLabel="Crear ciclo"
          title="Nuevo ciclo escolar"
        />
      ) : null}
    </>
  );
}
