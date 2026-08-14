import { useCallback, useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import ContentCopyOutlinedIcon from "@mui/icons-material/ContentCopyOutlined";
import PlayArrowOutlinedIcon from "@mui/icons-material/PlayArrowOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";

import {
  CYCLE_STATUS_LABEL,
  CYCLE_STATUS_VARIANT,
  cyclesService,
} from "@cycles/cyclesService.js";
import { PAGE_SIZE } from "@academics/academicsService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDate } from "@shared/utils/format.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { ConfirmActionButton } from "@ui/buttons/ConfirmActionButton.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

import { CycleDetailWindow } from "./CycleDetailWindow.jsx";

const CYCLE_COLUMNS = [
  { key: "year", label: "Ano", align: "right", render: (row) => row.year },
  { key: "name", label: "Ciclo", render: (row) => row.name },
  {
    key: "range",
    label: "Vigencia",
    render: (row) =>
      `${formatDate(row.starts_on)} — ${formatDate(row.ends_on)}`,
  },
  {
    key: "description",
    label: "Descripcion",
    render: (row) => row.description || <MutedCell>Sin descripcion</MutedCell>,
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

const CYCLE_FIELDS = [
  { name: "year", label: "Ano", type: "number", min: 2000, required: true },
  {
    name: "name",
    label: "Nombre del ciclo",
    required: true,
    placeholder: "Ejemplo: Ciclo 2027",
  },
  { name: "starts_on", label: "Inicio", type: "date", required: true },
  { name: "ends_on", label: "Cierre", type: "date", required: true },
  { name: "description", label: "Descripcion (opcional)", span: "full" },
];

const CLONE_FIELDS = [
  ...CYCLE_FIELDS,
  {
    name: "include_teaching_assignments",
    label: "Copiar tambien las asignaciones docentes",
    type: "checkbox",
    help: "Apagado por defecto: arrastrar asignaciones reasignaria personal que quizas ya no esta en el establecimiento.",
  },
];

/** Valores iniciales de un ciclo nuevo, derivados del que se esta clonando. */
function nextCycleDraft(source) {
  const year = (source?.year ?? new Date().getFullYear()) + 1;
  return {
    year,
    name: `Ciclo ${year}`,
    starts_on: "",
    ends_on: "",
    description: "",
    include_teaching_assignments: false,
  };
}

/**
 * Ciclos escolares: registro, activacion, clonado de estructura y consulta del
 * detalle historico.
 *
 * El ciclo es la raiz temporal de casi todo el sistema (oferta de grados,
 * matricula, asignaciones, evaluacion), por eso su estado se muestra siempre y
 * las acciones que lo cambian piden confirmacion explicita.
 */
export function CyclesPage() {
  const loadCycles = useCallback((params) => cyclesService.list(params), []);
  const list = usePaginatedList(loadCycles, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  const [creating, setCreating] = useState(false);
  const [cloning, setCloning] = useState(null);
  const [viewing, setViewing] = useState(null);
  const [actionError, setActionError] = useState("");

  const handleCreate = async (payload) => {
    // El interruptor de asignaciones solo existe al clonar; el alta no lo acepta.
    const { include_teaching_assignments: _ignored, ...cycle } = payload;
    await cyclesService.create(cycle);
    setCreating(false);
    list.refresh();
  };

  const handleClone = async (payload) => {
    await cyclesService.clone(cloning.public_id, payload);
    setCloning(null);
    list.refresh();
  };

  const handleActivate = async (cycle) => {
    setActionError("");
    try {
      await cyclesService.activate(cycle.public_id);
      list.refresh();
    } catch (requestError) {
      setActionError(requestError.message);
      throw requestError;
    }
  };

  return (
    <>
      <PageHeader
        action={
          <Button
            onClick={() => setCreating(true)}
            startIcon={<AddIcon fontSize="small" />}
            variant="contained"
          >
            Nuevo ciclo
          </Button>
        }
        breadcrumb="Estructura institucional"
        subtitle="Registro de ciclos escolares. Activar un ciclo cierra el anterior; un ciclo cerrado ya no acepta escrituras."
        title="Ciclo escolar"
      />

      <ListSection
        actionError={actionError}
        columns={CYCLE_COLUMNS}
        emptyMessage="Todavia no hay ciclos registrados."
        fillHeight
        getRowKey={(cycle) => cycle.public_id}
        list={list}
        renderActions={(cycle) => (
          <Stack direction="row" gap={0.5} justifyContent="flex-end">
            <ActionIconButton
              label="Ver detalle historico"
              onClick={() => setViewing(cycle)}
            >
              <VisibilityOutlinedIcon fontSize="small" />
            </ActionIconButton>
            <ActionIconButton
              label="Clonar estructura a un ciclo nuevo"
              onClick={() => setCloning(cycle)}
            >
              <ContentCopyOutlinedIcon fontSize="small" />
            </ActionIconButton>
            {cycle.status === "draft" ? (
              <ConfirmActionButton
                color="primary"
                confirmLabel="Si, activar"
                label="Activar"
                onConfirm={() => handleActivate(cycle)}
                question={`Se activara "${cycle.name}" como ciclo vigente. El ciclo activo anterior queda cerrado y deja de aceptar escrituras.`}
                title="Activar ciclo escolar"
              />
            ) : null}
            {cycle.status === "active" ? (
              <StatusChip label="Vigente" variant="success" />
            ) : null}
          </Stack>
        )}
        showInactiveToggle={false}
        subtitle="Ciclos del establecimiento"
        title="Ciclos registrados"
      />

      <EntityFormWindow
        description="El ciclo nace en borrador. Se vuelve vigente cuando se activa."
        fields={CYCLE_FIELDS}
        initialValues={nextCycleDraft()}
        key={creating ? "cycle-create-open" : "cycle-create-closed"}
        onCancel={() => setCreating(false)}
        onSubmit={handleCreate}
        open={creating}
        submitLabel="Crear ciclo"
        title="Nuevo ciclo escolar"
      />

      {cloning ? (
        <EntityFormWindow
          description={`Se copiara la estructura academica de "${cloning.name}" (oferta de grados, secciones y plan de estudios) al ciclo nuevo.`}
          fields={CLONE_FIELDS}
          initialValues={nextCycleDraft(cloning)}
          key={`clone-${cloning.public_id}`}
          onCancel={() => setCloning(null)}
          onSubmit={handleClone}
          open
          submitLabel="Clonar estructura"
          title={`Clonar ${cloning.name}`}
        />
      ) : null}

      {viewing ? (
        <CycleDetailWindow
          cycle={viewing}
          key={viewing.public_id}
          onClose={() => setViewing(null)}
        />
      ) : null}
    </>
  );
}
