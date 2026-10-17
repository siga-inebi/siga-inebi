import { lazy, Suspense, useCallback, useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import AddIcon from "@mui/icons-material/Add";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import PlaylistAddCheckOutlinedIcon from "@mui/icons-material/PlaylistAddCheckOutlined";
import ReplayOutlinedIcon from "@mui/icons-material/ReplayOutlined";
import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";

import { PAGE_SIZE } from "@academics/academicsService.js";
import {
  ENROLMENT_STATUS_LABEL,
  ENROLMENT_STATUS_VARIANT,
  enrolmentsService,
} from "@enrolments/enrolmentsService.js";
import { EnrolmentStudentFilter } from "./EnrolmentStudentFilter.jsx";
import { ListSection } from "@shared/crud/ListSection.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDate } from "@shared/utils/format.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { FilterBar } from "@ui/filters/FilterBar.jsx";
import { PageHeader } from "@ui/layout/PageHeader.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";
import { EmptyState } from "@ui/feedback/EmptyState.jsx";
import { MutedCell } from "@ui/table/cells.jsx";

// Estos flujos se abren solo por accion explicita. Cargarlos bajo demanda evita
// que la ruta de matriculas consuma el presupuesto de la pantalla inicial sin
// cambiar los contratos ni la experiencia de sus ventanas.
const BulkEnrolmentWindow = lazy(() =>
  import("./BulkEnrolmentWindow.jsx").then(
    ({ BulkEnrolmentWindow: Window }) => ({
      default: Window,
    })
  )
);
const EnrolmentDocumentsWindow = lazy(() =>
  import("./EnrolmentDocumentsWindow.jsx").then(
    ({ EnrolmentDocumentsWindow: Window }) => ({ default: Window })
  )
);
const MovementHistoryWindow = lazy(() =>
  import("./MovementHistoryWindow.jsx").then(
    ({ MovementHistoryWindow: Window }) => ({ default: Window })
  )
);

const EnrolmentCreateWindow = lazy(() =>
  import("./EnrolmentCreateWindow.jsx").then(
    ({ EnrolmentCreateWindow: Window }) => ({ default: Window })
  )
);

const ACTIVE_TAB = "active";
const HISTORY_TAB = "history";

/**
 * Matricula: matriculas vigentes e historial por estudiante.
 *
 * Las dos pestanas no son el mismo listado filtrado. "Vigentes" responde
 * `/active/` y admite consultar sin estudiante; "Historial" responde
 * `/history/`, que EXIGE `student_id` porque devuelve tambien las matriculas
 * inactivas de esa persona (RF-MAT-008). Por eso la pestana de historial pide el
 * estudiante antes de consultar en vez de mostrar una tabla vacia.
 *
 * El backend pide cinco identificadores para matricular (estudiante, ciclo,
 * grado, jornada y seccion), pero solo tres son decisiones reales: la seccion YA
 * pertenece a un grado y a una jornada. El formulario pide seccion y deriva los
 * otros dos de ella. Pedirlos por separado no le daba libertad a nadie, solo la
 * posibilidad de contradecirse y recibir un rechazo al guardar.
 */
export function EnrolmentsPage() {
  const [tab, setTab] = useState(ACTIVE_TAB);
  const [studentFilter, setStudentFilter] = useState(null);
  const [creating, setCreating] = useState(null);
  const [bulkEnrolling, setBulkEnrolling] = useState(false);
  const [documentsFor, setDocumentsFor] = useState(null);
  const [movementStudentId, setMovementStudentId] = useState("");

  const loadActive = useCallback(
    (params) =>
      enrolmentsService.listActive({
        ...params,
        student_id: studentFilter?.value,
      }),
    [studentFilter]
  );

  const loadHistory = useCallback(
    (params) =>
      enrolmentsService.listHistory({
        ...params,
        student_id: studentFilter?.value,
      }),
    [studentFilter]
  );

  const activeList = usePaginatedList(
    tab === ACTIVE_TAB ? loadActive : EMPTY_LOADER,
    {
      canIncludeInactive: false,
      pageSize: PAGE_SIZE,
    }
  );

  const historyReady = Boolean(studentFilter);
  const historyList = usePaginatedList(
    tab === HISTORY_TAB && historyReady ? loadHistory : EMPTY_LOADER,
    {
      canIncludeInactive: false,
      pageSize: PAGE_SIZE,
    }
  );

  const changeStudentFilter = (option) => {
    activeList.goToPage(1);
    historyList.goToPage(1);
    setStudentFilter(option);
  };

  const columns = [
    {
      key: "student_id",
      label: "Estudiante",
      render: (row) =>
        row.student ? (
          [row.student.full_name, row.student.student_code]
            .filter(Boolean)
            .join(" · ")
        ) : (
          <MutedCell>Estudiante no disponible</MutedCell>
        ),
    },
    {
      key: "academic_cycle_id",
      label: "Ciclo",
      render: (row) =>
        row.academic_cycle?.name || <MutedCell>Ciclo no disponible</MutedCell>,
    },
    {
      key: "grade_id",
      label: "Grado",
      render: (row) =>
        row.grade?.name || <MutedCell>Grado no disponible</MutedCell>,
    },
    {
      key: "section_id",
      label: "Seccion",
      render: (row) =>
        row.section ? (
          [
            [row.section.grade_name, row.section.name]
              .filter(Boolean)
              .join(" "),
            row.section.shift_name,
          ]
            .filter(Boolean)
            .join(" · ")
        ) : (
          <MutedCell>Seccion no disponible</MutedCell>
        ),
    },
    {
      key: "effective_on",
      label: "Vigente desde",
      render: (row) => formatDate(row.effective_on),
    },
    {
      key: "ends_on",
      label: "Hasta",
      render: (row) =>
        row.ends_on ? (
          formatDate(row.ends_on)
        ) : (
          <MutedCell>Sin cierre</MutedCell>
        ),
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
            onClick={() => setDocumentsFor(row)}
          >
            <DescriptionOutlinedIcon fontSize="small" />
          </ActionIconButton>
        </Stack>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        action={
          <Stack direction="row" flexWrap="wrap" gap={1}>
            <Button
              disabled={!studentFilter}
              onClick={() => setMovementStudentId(studentFilter.value)}
              startIcon={<HistoryOutlinedIcon fontSize="small" />}
              variant="text"
            >
              Movimientos
            </Button>
            <Button
              onClick={() => setBulkEnrolling(true)}
              startIcon={<PlaylistAddCheckOutlinedIcon fontSize="small" />}
              variant="outlined"
            >
              Matricular por lotes
            </Button>
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
          onClear={studentFilter ? () => changeStudentFilter(null) : undefined}
        >
          <EnrolmentStudentFilter
            selected={studentFilter}
            onChange={changeStudentFilter}
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
            <EmptyState message="El historial se consulta por estudiante: elija uno en el filtro de arriba para verlo." />
          </SectionCard>
        )}
      </SectionCard>

      <Suspense fallback={null}>
        {creating ? (
          <EnrolmentCreateWindow
            creating={creating}
            onCancel={() => setCreating(null)}
            onCreated={() => {
              setCreating(null);
              activeList.refresh();
              if (historyReady) historyList.refresh();
            }}
          />
        ) : null}
      </Suspense>

      <Suspense fallback={null}>
        {bulkEnrolling ? (
          <BulkEnrolmentWindow
            onClose={() => setBulkEnrolling(false)}
            onCreated={() => {
              activeList.refresh();
              if (historyReady) historyList.refresh();
            }}
          />
        ) : null}

        {documentsFor ? (
          <EnrolmentDocumentsWindow
            enrolment={documentsFor}
            key={documentsFor.public_id}
            onClose={() => setDocumentsFor(null)}
          />
        ) : null}

        {movementStudentId ? (
          <MovementHistoryWindow
            key={movementStudentId}
            onClose={() => setMovementStudentId("")}
            studentId={movementStudentId}
          />
        ) : null}
      </Suspense>
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
