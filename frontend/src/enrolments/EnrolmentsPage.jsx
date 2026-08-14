import { useCallback, useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Typography from "@mui/material/Typography";
import AddIcon from "@mui/icons-material/Add";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import ReplayOutlinedIcon from "@mui/icons-material/ReplayOutlined";

import { PAGE_SIZE } from "@academics/academicsService.js";
import {
  ENROLMENT_STATUS_LABEL,
  ENROLMENT_STATUS_VARIANT,
  enrolmentsService,
} from "@enrolments/enrolmentsService.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDate } from "@shared/utils/format.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { SearchField } from "@ui/filters/SearchField.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";
import { EmptyState } from "@ui/feedback/EmptyState.jsx";
import { CodeCell, MutedCell } from "@ui/table/cells.jsx";

import { EnrolmentDocumentsWindow } from "./EnrolmentDocumentsWindow.jsx";

/** Campos de matriculacion y de reinscripcion: el backend pide los mismos. */
const ENROLMENT_FIELDS = [
  { name: "student_id", label: "ID de estudiante", required: true, span: "full" },
  { name: "academic_cycle_id", label: "ID de ciclo escolar", required: true },
  { name: "grade_id", label: "ID de grado", required: true },
  { name: "shift_id", label: "ID de jornada", required: true },
  { name: "section_id", label: "ID de seccion", required: true },
  { name: "effective_on", label: "Vigente desde", type: "date", required: true },
];

const EMPTY_ENROLMENT = {
  student_id: "",
  academic_cycle_id: "",
  grade_id: "",
  shift_id: "",
  section_id: "",
  effective_on: "",
};

const ACTIVE_TAB = "active";
const HISTORY_TAB = "history";

function enrolmentColumns({ onOpenDocuments }) {
  return [
    {
      key: "student_id",
      label: "Estudiante",
      render: (row) => <CodeCell value={row.student_id} />,
    },
    {
      key: "academic_cycle_id",
      label: "Ciclo",
      render: (row) => <CodeCell value={row.academic_cycle_id} />,
    },
    { key: "grade_id", label: "Grado", render: (row) => <CodeCell value={row.grade_id} /> },
    { key: "section_id", label: "Seccion", render: (row) => <CodeCell value={row.section_id} /> },
    {
      key: "effective_on",
      label: "Vigente desde",
      render: (row) => formatDate(row.effective_on),
    },
    {
      key: "ends_on",
      label: "Hasta",
      render: (row) => (row.ends_on ? formatDate(row.ends_on) : <MutedCell>Sin cierre</MutedCell>),
    },
    {
      key: "status",
      label: "Estado",
      render: (row) => (
        <StatusChip
          label={ENROLMENT_STATUS_LABEL[row.status] ?? row.status}
          variant={ENROLMENT_STATUS_VARIANT[row.status] ?? "neutral"}
        />
      ),
    },
    {
      key: "acciones",
      label: "Acciones",
      align: "right",
      render: (row) => (
        <Stack direction="row" gap={0.5} justifyContent="flex-end">
          <ActionIconButton
            label="Requisitos documentales"
            onClick={() => onOpenDocuments(row)}
          >
            <DescriptionOutlinedIcon fontSize="small" />
          </ActionIconButton>
        </Stack>
      ),
    },
  ];
}

/**
 * Matricula: matriculas vigentes e historial por estudiante.
 *
 * Las dos pestanas no son el mismo listado filtrado. "Vigentes" responde
 * `/active/` y admite consultar sin estudiante; "Historial" responde
 * `/history/`, que EXIGE `student_id` porque devuelve tambien las matriculas
 * inactivas de esa persona (RF-MAT-008). Por eso la pestana de historial pide el
 * identificador antes de consultar en vez de mostrar una tabla vacia.
 */
export function EnrolmentsPage() {
  const [tab, setTab] = useState(ACTIVE_TAB);
  const [studentFilter, setStudentFilter] = useState("");
  const [creating, setCreating] = useState(null);
  const [documentsFor, setDocumentsFor] = useState(null);

  const loadActive = useCallback(
    (params) =>
      enrolmentsService.listActive({
        ...params,
        student_id: studentFilter.trim() || undefined,
      }),
    [studentFilter]
  );

  const loadHistory = useCallback(
    (params) => enrolmentsService.listHistory({ ...params, student_id: studentFilter.trim() }),
    [studentFilter]
  );

  const activeList = usePaginatedList(loadActive, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  const historyReady = studentFilter.trim() !== "";
  const historyList = usePaginatedList(historyReady ? loadHistory : EMPTY_LOADER, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  const columns = enrolmentColumns({ onOpenDocuments: setDocumentsFor });

  const handleSubmit = async (payload) => {
    if (creating === "reenrol") {
      await enrolmentsService.reenrol(payload);
    } else {
      await enrolmentsService.matriculate(payload);
    }
    setCreating(null);
    activeList.refresh();
    if (historyReady) historyList.refresh();
  };

  return (
    <>
      <PageHeader
        action={
          <Stack direction="row" gap={1}>
            <Button
              onClick={() => setCreating("reenrol")}
              startIcon={<ReplayOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              Reinscribir
            </Button>
            <Button
              onClick={() => setCreating("matriculate")}
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Nueva matricula
            </Button>
          </Stack>
        }
        breadcrumb="Matricula"
        subtitle="Matriculas vigentes del ciclo e historial por estudiante. La matriculacion valida cupo de seccion y jornada antes de registrar."
        title="Matriculas"
      />

      <SectionCard fillHeight marker={false} sx={{ border: "none" }}>
        <Tabs
          onChange={(_event, next) => setTab(next)}
          sx={{ borderBottom: "1px solid", borderColor: "divider", mb: 2 }}
          value={tab}
        >
          <Tab label="Vigentes" value={ACTIVE_TAB} />
          <Tab label="Historial por estudiante" value={HISTORY_TAB} />
        </Tabs>

        <FilterBar
          onClear={studentFilter ? () => setStudentFilter("") : undefined}
        >
          <SearchField
            onChange={setStudentFilter}
            placeholder="Filtrar por ID de estudiante…"
            value={studentFilter}
          />
        </FilterBar>

        {tab === ACTIVE_TAB ? (
          <ListSection
            columns={columns}
            emptyMessage={
              studentFilter
                ? "Este estudiante no tiene matricula vigente."
                : "Todavia no hay matriculas vigentes."
            }
            fillHeight
            getRowKey={(row) => row.public_id}
            list={activeList}
            showInactiveToggle={false}
            subtitle="Solo matriculas activas del ciclo vigente"
            title="Matriculas vigentes"
          />
        ) : historyReady ? (
          <ListSection
            columns={columns}
            emptyMessage="Este estudiante no tiene matriculas registradas."
            fillHeight
            getRowKey={(row) => row.public_id}
            list={historyList}
            showInactiveToggle={false}
            subtitle="Incluye matriculas cerradas, retiradas y anuladas"
            title="Historial de matricula"
          />
        ) : (
          <SectionCard title="Historial de matricula">
            <EmptyState
              message="El historial se consulta por estudiante: escribe un ID de estudiante en el filtro para verlo."
            />
          </SectionCard>
        )}
      </SectionCard>

      {creating ? (
        <EntityFormWindow
          description={
            creating === "reenrol"
              ? "Reinscripcion de un estudiante con matricula previa. El backend valida que exista historial y que el ciclo destino este abierto."
              : "Matriculacion nueva. El backend valida cupo de la seccion, jornada y requisitos del ciclo."
          }
          fields={ENROLMENT_FIELDS}
          initialValues={EMPTY_ENROLMENT}
          key={creating}
          onCancel={() => setCreating(null)}
          onSubmit={handleSubmit}
          open
          submitLabel={creating === "reenrol" ? "Reinscribir" : "Matricular"}
          title={creating === "reenrol" ? "Reinscribir estudiante" : "Nueva matricula"}
        />
      ) : null}

      {documentsFor ? (
        <EnrolmentDocumentsWindow
          enrolment={documentsFor}
          key={documentsFor.public_id}
          onClose={() => setDocumentsFor(null)}
        />
      ) : null}
    </>
  );
}

/**
 * Cargador inerte para la pestana de historial cuando todavia no hay estudiante.
 *
 * `usePaginatedList` siempre consulta al montarse; sin esto la pestana dispararia
 * una peticion sin `student_id`, que el backend rechaza con 400. Devolver una
 * pagina vacia deja el hook en un estado valido sin tocar la red.
 */
const EMPTY_LOADER = () => Promise.resolve({ count: 0, results: [] });
