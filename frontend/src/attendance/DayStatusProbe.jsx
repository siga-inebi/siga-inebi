import { useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import SearchIcon from "@mui/icons-material/Search";

import {
  attendanceService,
  MOVEMENT_LABEL,
} from "@attendance/attendanceService.js";
import {
  useShiftCatalog,
  useStudentCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { formatDateTime, todayInputValue } from "@shared/utils/format.js";
import { StatusChip } from "@ui/display/StatusChip.jsx";
import { EmptyState } from "@ui/feedback/EmptyState.jsx";
import { DateField } from "@ui/forms/DateField.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";
import { DetailField } from "@ui/layout/DetailWindow.jsx";

/** Estado del dia calculado por el backend -> variante semantica. */
const DAY_STATUS_VARIANT = {
  presente: "success",
  tarde: "warning",
  ausente: "danger",
  permanencia_sin_cierre: "warning",
};

/**
 * Consulta puntual del estado del dia de un estudiante.
 *
 * Es un formulario y no un listado porque el endpoint exige los tres
 * identificadores: no existe un "listar el estado de todos". Mostrar una tabla
 * vacia esperando datos que nunca van a llegar seria enganoso, asi que la
 * pantalla pide explicitamente los tres valores y recien entonces consulta.
 *
 * Estudiante y jornada se eligen de su catalogo: son identificadores internos,
 * y quien consulta el estado del dia conoce el nombre de la persona, no su UUID.
 * La fecha arranca en hoy, que es lo que se consulta el 99% de las veces.
 */
export function DayStatusProbe() {
  const students = useStudentCatalog();
  const shifts = useShiftCatalog();

  const [studentId, setStudentId] = useState("");
  const [shiftId, setShiftId] = useState("");
  // Arranca en hoy: el estado del dia que alguien consulta es, casi siempre, el
  // de hoy. Empezar vacio obligaba a llenar la fecha en cada consulta para
  // preguntar lo mismo.
  const [eventDate, setEventDate] = useState(todayInputValue);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const canSubmit =
    studentId !== "" && shiftId !== "" && eventDate !== "" && !loading;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) return;

    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await attendanceService.dayStatus({
        student_id: studentId,
        shift_id: shiftId,
        event_date: eventDate,
      });
      setResult(data);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SectionCard
      subtitle="Requiere estudiante, jornada y fecha"
      sx={{ height: "100%" }}
      title="Estado del dia"
    >
      <Box component="form" onSubmit={handleSubmit} sx={{ px: 3, py: 2.5 }}>
        <Stack gap={2}>
          <FormSelect
            error={students.error}
            fullWidth
            helperText={
              !students.loading && students.options.length === 0
                ? "No hay estudiantes registrados."
                : undefined
            }
            label="Estudiante"
            loading={students.loading}
            onChange={(event) => setStudentId(event.target.value)}
            options={students.options}
            placeholder="Seleccione un estudiante"
            value={studentId}
          />
          <Stack direction={{ xs: "column", sm: "row" }} gap={2}>
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
              value={shiftId}
            />
            <DateField
              label="Fecha"
              onChange={(event) => setEventDate(event.target.value)}
              value={eventDate}
            />
          </Stack>
          <Box>
            <Button
              disabled={!canSubmit}
              startIcon={
                loading ? (
                  <CircularProgress size={16} />
                ) : (
                  <SearchIcon fontSize="small" />
                )
              }
              type="submit"
              variant="contained"
            >
              Consultar
            </Button>
          </Box>

          {error ? <Alert severity="error">{error}</Alert> : null}

          {result ? (
            <Box
              component="dl"
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                gap: 2,
                m: 0,
                pt: 1,
                borderTop: "1px solid",
                borderColor: "divider",
              }}
            >
              <DetailField
                label="Estado"
                value={
                  result.status ? (
                    <StatusChip
                      label={result.status}
                      variant={DAY_STATUS_VARIANT[result.status] ?? "neutral"}
                    />
                  ) : (
                    "Sin estado calculado"
                  )
                }
              />
              <DetailField
                label="Evento de entrada"
                value={
                  result.entry_event
                    ? `${
                        MOVEMENT_LABEL[result.entry_event.movement_type] ??
                        result.entry_event.movement_type
                      } · ${formatDateTime(result.entry_event.captured_at)}`
                    : null
                }
              />
            </Box>
          ) : !error && !loading ? (
            <EmptyState message="Elija estudiante, jornada y fecha para consultar el estado del dia." />
          ) : null}
        </Stack>
      </Box>
    </SectionCard>
  );
}
