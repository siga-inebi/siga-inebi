import { useCallback, useMemo, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import SearchIcon from "@mui/icons-material/Search";

import { PAGE_SIZE } from "@academics/academicsService.js";
import { attendanceService } from "@attendance/attendanceService.js";
import {
  labelIndex,
  useGradeCatalog,
  useSectionCatalog,
  useShiftCatalog,
  useStudentCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDateTime, todayInputValue } from "@shared/utils/format.js";
import { EmptyState } from "@ui/feedback/EmptyState.jsx";
import { DateField } from "@ui/forms/DateField.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { CodeCell, MutedCell } from "@ui/table/cells.jsx";

/**
 * Nombre del catalogo, con el identificador crudo como respaldo.
 *
 * Una fila de presencia puede apuntar a un estudiante dado de baja o a una
 * seccion que ya no figura en el catalogo; la celda vacia se leeria como un
 * error del sistema, y el identificador al menos es rastreable.
 */
function nameCell(index, id) {
  return (
    index.get(id) ?? (id ? <CodeCell value={id} /> : <MutedCell>—</MutedCell>)
  );
}

const presenceColumns = (names) => [
  {
    key: "student_id",
    label: "Estudiante",
    render: (row) => nameCell(names.students, row.student_id),
  },
  {
    key: "section_id",
    label: "Seccion",
    render: (row) => nameCell(names.sections, row.section_id),
  },
  {
    key: "entry_event",
    label: "Hora de ingreso",
    render: (row) =>
      row.entry_event ? (
        formatDateTime(row.entry_event.captured_at)
      ) : (
        <MutedCell>Sin dato</MutedCell>
      ),
  },
];

/**
 * Consulta de presencia en tiempo real (RF-JOR-008): quien tiene ingreso
 * registrado y todavia no tiene egreso, para una jornada y fecha.
 *
 * Igual que "Estado del dia", exige la jornada antes de consultar: sin eso no
 * hay nada sensato que listar. Jornada, grado y seccion salen de su catalogo —
 * se pedian como "ID de jornada", "ID de grado" e "ID de seccion", que son
 * UUIDs que solo existen en la base de datos. La fecha arranca en hoy, que es
 * la unica que tiene sentido para una consulta de "quien esta presente".
 *
 * Solo la jornada es obligatoria; grado y seccion acotan la busqueda.
 */
export function AttendancePresenceWindow({ onClose }) {
  const shifts = useShiftCatalog();
  const grades = useGradeCatalog();
  const sections = useSectionCatalog();
  const students = useStudentCatalog();

  const [shiftId, setShiftId] = useState("");
  const [eventDate, setEventDate] = useState(todayInputValue);
  const [gradeId, setGradeId] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [query, setQuery] = useState(null);

  const names = useMemo(
    () => ({
      students: labelIndex(students.options),
      sections: labelIndex(sections.options),
    }),
    [students.options, sections.options]
  );

  const loadPresence = useCallback(
    (params) => {
      if (!query) return Promise.resolve({ results: [], count: 0 });
      return attendanceService.listPresence({ ...params, ...query });
    },
    [query]
  );
  const list = usePaginatedList(loadPresence, {
    canIncludeInactive: false,
    pageSize: PAGE_SIZE,
  });

  const canSearch = shiftId !== "";

  // Las secciones se acotan al grado elegido: ofrecer las de otro grado lleva a
  // una combinacion que no devuelve nada y parece un sistema sin datos.
  const sectionOptions = gradeId
    ? sections.options.filter((option) => option.gradeId === gradeId)
    : sections.options;

  const handleSearch = (event) => {
    event.preventDefault();
    if (!canSearch) return;
    setQuery({
      shift_id: shiftId,
      ...(eventDate ? { event_date: eventDate } : null),
      ...(gradeId ? { grade_id: gradeId } : null),
      ...(sectionId ? { section_id: sectionId } : null),
    });
  };

  return (
    <FloatingWindow
      description="Estudiantes con ingreso registrado y sin egreso, en cualquier momento de la jornada."
      footer={
        <Button onClick={onClose} variant="text">
          Cerrar
        </Button>
      }
      onClose={onClose}
      open
      title="Presencia en tiempo real"
      width={WINDOW_WIDTH.wide}
    >
      <Stack gap={2}>
        <Box component="form" onSubmit={handleSearch}>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
              columnGap: 2,
              rowGap: 2.5,
            }}
          >
            <FormSelect
              error={shifts.error}
              fullWidth
              helperText={
                !shifts.loading && shifts.options.length === 0
                  ? "No hay jornadas registradas."
                  : undefined
              }
              label="Jornada"
              loading={shifts.loading}
              onChange={(event) => setShiftId(event.target.value)}
              options={shifts.options}
              placeholder="Seleccione una jornada"
              required
              value={shiftId}
            />
            <DateField
              fullWidth
              label="Fecha"
              onChange={(event) => setEventDate(event.target.value)}
              value={eventDate}
            />
            <FormSelect
              error={grades.error}
              fullWidth
              helperText="Opcional; acota el listado."
              label="Grado"
              loading={grades.loading}
              onChange={(event) => {
                setGradeId(event.target.value);
                // La seccion elegida pertenece al grado anterior: dejarla
                // seleccionada produce una consulta sin resultados.
                setSectionId("");
              }}
              options={grades.options}
              placeholder="Todos los grados"
              value={gradeId}
            />
            <FormSelect
              error={sections.error}
              fullWidth
              helperText="Opcional; acota el listado."
              label="Seccion"
              loading={sections.loading}
              onChange={(event) => setSectionId(event.target.value)}
              options={sectionOptions}
              placeholder="Todas las secciones"
              value={sectionId}
            />
          </Box>
          <Button
            disabled={!canSearch}
            startIcon={
              list.loading && query ? (
                <CircularProgress size={16} />
              ) : (
                <SearchIcon fontSize="small" />
              )
            }
            sx={{ mt: 2.5 }}
            type="submit"
            variant="contained"
          >
            Buscar
          </Button>
        </Box>

        {list.error ? <Alert severity="error">{list.error}</Alert> : null}

        {query ? (
          <DataTable
            columns={presenceColumns(names)}
            emptyMessage="Nadie presente sin egreso para estos filtros."
            getRowKey={(row) => row.student_id}
            loading={list.loading}
            pagination={list.pagination}
            rows={list.items}
          />
        ) : (
          <EmptyState message="Elija la jornada para consultar quien esta presente." />
        )}
      </Stack>
    </FloatingWindow>
  );
}
