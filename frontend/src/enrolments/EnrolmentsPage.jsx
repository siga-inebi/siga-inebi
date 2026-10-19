import { lazy, Suspense, useCallback, useState } from "react";

import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import SchoolOutlinedIcon from "@mui/icons-material/SchoolOutlined";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";
import ExitToAppOutlinedIcon from "@mui/icons-material/ExitToAppOutlined";

import { PAGE_SIZE } from "@academics/academicsService.js";
import { EnrolmentEntryMenu } from "@enrolments/EnrolmentEntryMenu.jsx";
import { EnrolmentAcademicFilters } from "./EnrolmentAcademicFilters.jsx";
import { EMPTY_ACADEMIC_FILTERS } from "./academicFilters.js";
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
const BulkReenrolmentWindow = lazy(() =>
  import("./BulkReenrolmentWindow.jsx").then(
    ({ BulkReenrolmentWindow: Window }) => ({ default: Window })
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
const StudentTransferWindow = lazy(() =>
  import("./StudentTransferWindow.jsx").then(
    ({ StudentTransferWindow: Window }) => ({ default: Window })
  )
);

const EnrolmentCreateWindow = lazy(() =>
  import("./EnrolmentCreateWindow.jsx").then(
    ({ EnrolmentCreateWindow: Window }) => ({ default: Window })
  )
);

const ACTIVE_TAB = "active";
const HISTORY_TAB = "history";

const PromotionWindow = lazy(() =>
  import("./PromotionWindow.jsx").then(({ PromotionWindow: Window }) => ({
    default: Window,
  }))
);

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
  const [transferFor, setTransferFor] = useState(null);
  const [tab, setTab] = useState(ACTIVE_TAB);
  const [academicFilters, setAcademicFilters] = useState(
    EMPTY_ACADEMIC_FILTERS
  );
  const [studentFilter, setStudentFilter] = useState(null);
  const [creating, setCreating] = useState(null);
  const [promotionFor, setPromotionFor] = useState(null);
  const [bulkEnrolling, setBulkEnrolling] = useState(false);
  const [bulkReenrolling, setBulkReenrolling] = useState(false);
  const [documentsFor, setDocumentsFor] = useState(null);
  const [movementFor, setMovementFor] = useState(null);
  const [movementStudentId, setMovementStudentId] = useState("");

  const loadActive = useCallback(
    (params) =>
      enrolmentsService.listActive({
        ...params,
        student_id: studentFilter?.value,
        academic_cycle_id: academicFilters.academic_cycle_id || undefined,
        grade_id: academicFilters.grade_id || undefined,
        section_id: academicFilters.section?.value,
      }),
    [studentFilter, academicFilters]
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
  const hasAcademicFilters = Boolean(
    academicFilters.academic_cycle_id ||
    academicFilters.grade_id ||
    academicFilters.section
  );
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
      key: "promotion",
      label: "Promoción",
      align: "center",
      render: (row) => (
        <ActionIconButton
          label="Consultar promoción"
          onClick={() =>
            setPromotionFor({
              enrolment: row,
              context: columns.slice(0, 4).map((column) => ({
                label: column.label,
                value: column.render(row),
              })),
            })
          }
        >
          <SchoolOutlinedIcon fontSize="small" />
        </ActionIconButton>
      ),
    },
    {
      key: "acciones",
      label: "Acciones",
      align: "right",
      render: (row) => (
        <Stack direction="row" gap={0.5} justifyContent="flex-end">
          <ActionIconButton
            label="Movimientos de matrícula"
            onClick={() =>
              setMovementFor({
                studentId: row.student_id,
                // Reuse the displayed cells with either catalogues or M1's nested DTO.
                studentLabel: columns
                  .find((column) => column.key === "student_id")
                  .render(row),
                enrolment: tab === ACTIVE_TAB ? row : undefined,
                enrolmentLabel: (
                  <Stack direction="row" flexWrap="wrap" gap={1}>
                    {["academic_cycle_id", "grade_id", "section_id"].map(
                      (key) => (
                        <span key={key}>
                          {columns
                            .find((column) => column.key === key)
                            .render(row)}
                        </span>
                      )
                    )}
                  </Stack>
                ),
              })
            }
          >
            <HistoryOutlinedIcon fontSize="small" />
          </ActionIconButton>
          <ActionIconButton
            label="Requisitos documentales"
            onClick={() => setDocumentsFor(row)}
          >
            <DescriptionOutlinedIcon fontSize="small" />
          </ActionIconButton>
          {tab === ACTIVE_TAB ? (
            <ActionIconButton
              label="Traslado de egreso"
              onClick={() =>
                setTransferFor({
                  direction: "out",
                  enrolment: row,
                  studentLabel: columns
                    .find((column) => column.key === "student_id")
                    .render(row),
                  enrolmentLabel: (
                    <Stack direction="row" flexWrap="wrap" gap={1}>
                      {["academic_cycle_id", "grade_id", "section_id"].map(
                        (key) => (
                          <span key={key}>
                            {columns
                              .find((column) => column.key === key)
                              .render(row)}
                          </span>
                        )
                      )}
                    </Stack>
                  ),
                })
              }
            >
              <ExitToAppOutlinedIcon fontSize="small" />
            </ActionIconButton>
          ) : null}
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
            <EnrolmentEntryMenu
              onIndividual={() => setCreating(true)}
              onInitialBulk={() => setBulkEnrolling(true)}
              onReenrolBulk={() => setBulkReenrolling(true)}
            />
            <Button
              onClick={() => setTransferFor({ direction: "in" })}
              variant="outlined"
            >
              Traslado de ingreso
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
          onClear={
            studentFilter || (tab === ACTIVE_TAB && hasAcademicFilters)
              ? () => {
                  setStudentFilter(null);
                  if (tab === ACTIVE_TAB)
                    setAcademicFilters(EMPTY_ACADEMIC_FILTERS);
                  activeList.goToPage(1);
                  historyList.goToPage(1);
                }
              : undefined
          }
        >
          <Stack
            direction={{ xs: "column", md: "row" }}
            flexWrap="wrap"
            gap={1.5}
            sx={{ minWidth: 0, flex: 1 }}
          >
            {tab === ACTIVE_TAB ? (
              <EnrolmentAcademicFilters
                value={academicFilters}
                onChange={(next) => {
                  setAcademicFilters(next);
                  activeList.goToPage(1);
                }}
              />
            ) : null}
            <EnrolmentStudentFilter
              selected={studentFilter}
              onChange={changeStudentFilter}
            />
          </Stack>
        </FilterBar>

        {tab === ACTIVE_TAB ? (
          <ListSection
            columns={columns}
            emptyMessage={
              studentFilter || hasAcademicFilters
                ? "No hay matrículas vigentes que coincidan con los filtros."
                : "Todavia no hay matriculas vigentes."
            }
            fillHeight
            getRowKey={(row) => row.public_id}
            list={activeList}
            showInactiveToggle={false}
            subtitle="Matrículas activas según los filtros seleccionados"
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
        {bulkReenrolling ? (
          <BulkReenrolmentWindow
            onClose={() => setBulkReenrolling(false)}
            onCreated={() => {
              activeList.refresh();
              if (historyReady) historyList.refresh();
            }}
          />
        ) : null}
        {bulkEnrolling ? (
          <BulkEnrolmentWindow
            onClose={() => setBulkEnrolling(false)}
            onCreated={() => {
              activeList.refresh();
              if (historyReady) historyList.refresh();
            }}
          />
        ) : null}

        {promotionFor ? (
          <PromotionWindow
            {...promotionFor}
            key={promotionFor.enrolment.public_id}
            onClose={() => setPromotionFor(null)}
          />
        ) : null}

        {documentsFor ? (
          <EnrolmentDocumentsWindow
            enrolment={documentsFor}
            key={documentsFor.public_id}
            onClose={() => setDocumentsFor(null)}
          />
        ) : null}

        {movementFor || movementStudentId ? (
          <MovementHistoryWindow
            key={
              movementFor?.enrolment?.public_id ??
              (movementStudentId || movementFor?.studentId)
            }
            onClose={() => {
              setMovementFor(null);
              setMovementStudentId("");
            }}
            studentId={movementStudentId}
            {...movementFor}
            onChanged={() => {
              activeList.refresh();
              if (historyReady) historyList.refresh();
            }}
          />
        ) : null}
        {transferFor ? (
          <StudentTransferWindow
            {...transferFor}
            onClose={() => setTransferFor(null)}
            onChanged={() => {
              activeList.refresh();
              if (historyReady) historyList.refresh();
            }}
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
