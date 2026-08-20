import { useCallback, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import SearchIcon from "@mui/icons-material/Search";

import { PAGE_SIZE } from "@academics/academicsService.js";
import { attendanceService } from "@attendance/attendanceService.js";
import { usePaginatedList } from "@shared/crud/usePaginatedList.js";
import { formatDateTime } from "@shared/utils/format.js";
import { EmptyState } from "@ui/feedback/EmptyState.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";
import { DataTable } from "@ui/table/DataTable.jsx";
import { CodeCell } from "@ui/table/cells.jsx";

const PRESENCE_COLUMNS = [
  {
    key: "student_id",
    label: "Estudiante",
    render: (row) => <CodeCell value={row.student_id} />,
  },
  {
    key: "section_id",
    label: "Seccion",
    render: (row) => <CodeCell value={row.section_id} />,
  },
  {
    key: "entry_event",
    label: "Hora de ingreso",
    render: (row) =>
      row.entry_event ? formatDateTime(row.entry_event.captured_at) : "—",
  },
];

/**
 * Consulta de presencia en tiempo real (RF-JOR-008): quien tiene ingreso
 * registrado y todavia no tiene egreso, para una jornada y fecha.
 *
 * Igual que "Estado del dia", exige la jornada antes de consultar: sin eso no
 * hay nada sensato que listar. `shift_id` es el unico campo obligatorio;
 * fecha, grado y seccion acotan la busqueda.
 */
export function AttendancePresenceWindow({ onClose }) {
  const [shiftId, setShiftId] = useState("");
  const [eventDate, setEventDate] = useState("");
  const [gradeId, setGradeId] = useState("");
  const [sectionId, setSectionId] = useState("");
  const [query, setQuery] = useState(null);

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

  const canSearch = shiftId.trim() !== "";

  const handleSearch = (event) => {
    event.preventDefault();
    if (!canSearch) return;
    setQuery({
      shift_id: shiftId.trim(),
      ...(eventDate ? { event_date: eventDate } : null),
      ...(gradeId.trim() ? { grade_id: gradeId.trim() } : null),
      ...(sectionId.trim() ? { section_id: sectionId.trim() } : null),
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
          <Stack
            direction={{ xs: "column", sm: "row" }}
            flexWrap="wrap"
            gap={2}
          >
            <FormTextField
              label="ID de jornada"
              onChange={(event) => setShiftId(event.target.value)}
              required
              value={shiftId}
            />
            <FormTextField
              label="Fecha"
              onChange={(event) => setEventDate(event.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              type="date"
              value={eventDate}
            />
            <FormTextField
              label="ID de grado"
              onChange={(event) => setGradeId(event.target.value)}
              value={gradeId}
            />
            <FormTextField
              label="ID de seccion"
              onChange={(event) => setSectionId(event.target.value)}
              value={sectionId}
            />
            <Button
              disabled={!canSearch}
              startIcon={
                list.loading && query ? (
                  <CircularProgress size={16} />
                ) : (
                  <SearchIcon fontSize="small" />
                )
              }
              sx={{ alignSelf: { xs: "stretch", sm: "flex-end" } }}
              type="submit"
              variant="contained"
            >
              Buscar
            </Button>
          </Stack>
        </Box>

        {list.error ? <Alert severity="error">{list.error}</Alert> : null}

        {query ? (
          <DataTable
            columns={PRESENCE_COLUMNS}
            emptyMessage="Nadie presente sin egreso para estos filtros."
            getRowKey={(row) => row.student_id}
            loading={list.loading}
            pagination={list.pagination}
            rows={list.items}
          />
        ) : (
          <EmptyState message="Ingresa al menos la jornada para consultar quien esta presente." />
        )}
      </Stack>
    </FloatingWindow>
  );
}
