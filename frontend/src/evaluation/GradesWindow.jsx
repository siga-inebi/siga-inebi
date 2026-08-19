import { useCallback, useMemo, useState } from "react";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import QueryStatsOutlinedIcon from "@mui/icons-material/QueryStatsOutlined";

import { PAGE_SIZE } from "@academics/academicsService.js";
import { evaluationService } from "@evaluation/evaluationService.js";
import {
  asTeacherPersonOptions,
  labelIndex,
  useEnrolmentCatalog,
  useSubjectCatalog,
  useTeacherCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDateTime } from "@shared/utils/format.js";
import { ActionIconButton } from "@ui/buttons/ActionIconButton.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { CodeCell, MutedCell } from "@ui/table/cells.jsx";

import { CurrentAverageWindow } from "./CurrentAverageWindow.jsx";

/** Nombre del catalogo, con el identificador crudo como respaldo. */
function nameCell(index, id) {
  return (
    index.get(id) ?? (id ? <CodeCell value={id} /> : <MutedCell>—</MutedCell>)
  );
}

function buildGradeColumns(onViewAverage, names) {
  return [
    {
      key: "enrolment",
      label: "Estudiante",
      render: (row) => nameCell(names.enrolments, row.enrolment),
    },
    {
      key: "subject",
      label: "Subarea",
      render: (row) => nameCell(names.subjects, row.subject),
    },
    { key: "value", label: "Nota", align: "right", render: (row) => row.value },
    {
      key: "updated_at",
      label: "Ultima actualizacion",
      render: (row) => formatDateTime(row.updated_at),
    },
    {
      key: "acciones",
      label: "Acciones",
      align: "right",
      render: (row) => (
        <ActionIconButton
          label="Promedio en curso de esta inscripcion y subarea"
          onClick={() => onViewAverage(row)}
        >
          <QueryStatsOutlinedIcon fontSize="small" />
        </ActionIconButton>
      ),
    },
  ];
}

const gradeFields = ({ enrolments, subjects, teacherPeople, teachers }) => [
  {
    name: "enrolment",
    label: "Estudiante",
    type: "select",
    options: enrolments.options,
    loading: enrolments.loading,
    optionsError: enrolments.error,
    emptyHint: "No hay matriculas vigentes.",
    required: true,
    help: "La nota se registra contra la matricula, que ata al estudiante con su seccion y su ciclo.",
    span: "full",
  },
  {
    name: "subject",
    label: "Subarea",
    type: "select",
    options: subjects.options,
    loading: subjects.loading,
    optionsError: subjects.error,
    emptyHint: "No hay cursos registrados.",
    required: true,
  },
  {
    name: "teacher",
    label: "Docente",
    type: "select",
    options: teacherPeople,
    loading: teachers.loading,
    optionsError: teachers.error,
    emptyHint: "No hay docentes registrados.",
    required: true,
  },
  {
    name: "value",
    label: "Nota",
    type: "number",
    min: 0,
    required: true,
    help: "Escala de 0 a 100. Nota ya calculada por el docente para esta unidad; el sistema no la deriva de actividades.",
    span: "full",
  },
];

/**
 * Notas de una unidad de evaluacion (RF-CAL-001).
 *
 * Registrar de nuevo la misma inscripcion/subarea actualiza la nota existente
 * en vez de duplicarla: es el valor consolidado unico de esa combinacion. El
 * backend rechaza el registro si la ventana de captura esta cerrada y no hay
 * una excepcion vigente para ese docente y esa subarea.
 */
export function GradesWindow({ cycleId, onClose, unit }) {
  const enrolments = useEnrolmentCatalog();
  const subjects = useSubjectCatalog();
  const teachers = useTeacherCatalog();

  const teacherPeople = useMemo(
    () => asTeacherPersonOptions(teachers.options),
    [teachers.options]
  );
  const names = useMemo(
    () => ({
      enrolments: labelIndex(enrolments.options),
      subjects: labelIndex(subjects.options),
    }),
    [enrolments.options, subjects.options]
  );

  const loadGrades = useCallback(
    (params) => evaluationService.listGrades(cycleId, unit.public_id, params),
    [cycleId, unit.public_id]
  );
  const list = usePaginatedList(loadGrades, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  const [registering, setRegistering] = useState(false);
  const [averageFor, setAverageFor] = useState(null);

  const handleRegister = async (payload) => {
    await evaluationService.registerGrade(cycleId, unit.public_id, payload);
    setRegistering(false);
    list.refresh();
  };

  const columns = buildGradeColumns(setAverageFor, names);

  return (
    <>
      <FloatingWindow
        description={`Notas registradas para "${unit.name}". Volver a registrar la misma inscripcion y subarea actualiza la nota.`}
        footer={
          <>
            <Button onClick={onClose} variant="text">
              Cerrar
            </Button>
            <Button
              onClick={() => setRegistering(true)}
              startIcon={<AddIcon fontSize="small" />}
              variant="contained"
            >
              Registrar nota
            </Button>
          </>
        }
        onClose={onClose}
        open
        title="Notas de la unidad"
        width={WINDOW_WIDTH.wide}
      >
        <Stack gap={2}>
          {list.error ? <Alert severity="error">{list.error}</Alert> : null}
          <DataTable
            columns={columns}
            emptyMessage="Esta unidad todavia no tiene notas registradas."
            getRowKey={(row) => row.public_id}
            loading={list.loading}
            pagination={list.pagination}
            rows={list.items}
          />
        </Stack>
      </FloatingWindow>

      {registering ? (
        <EntityFormWindow
          description="La nota ya viene calculada por el docente: el sistema solo la almacena."
          fields={gradeFields({
            enrolments,
            subjects,
            teacherPeople,
            teachers,
          })}
          initialValues={{ enrolment: "", subject: "", teacher: "", value: "" }}
          key="register-grade"
          onCancel={() => setRegistering(false)}
          onSubmit={handleRegister}
          open
          submitLabel="Registrar nota"
          title="Nueva nota de unidad"
        />
      ) : null}

      {averageFor ? (
        <CurrentAverageWindow
          cycleId={cycleId}
          enrolmentId={averageFor.enrolment}
          key={`${averageFor.enrolment}-${averageFor.subject}`}
          onClose={() => setAverageFor(null)}
          subjectId={averageFor.subject}
        />
      ) : null}
    </>
  );
}
