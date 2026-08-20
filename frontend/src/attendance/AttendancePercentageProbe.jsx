import { useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import SearchIcon from "@mui/icons-material/Search";

import { attendanceService } from "@attendance/attendanceService.js";
import {
  useShiftCatalog,
  useStudentCatalog,
} from "@shared/catalogs/academicCatalogs.js";
import { todayInputValue } from "@shared/utils/format.js";
import { StatCard } from "@ui/display/StatCard.jsx";
import { EmptyState } from "@ui/feedback/EmptyState.jsx";
import { DateField } from "@ui/forms/DateField.jsx";
import { FormSelect } from "@ui/forms/FormSelect.jsx";
import { SectionCard } from "@ui/layout/SectionCard.jsx";
import { DetailField } from "@ui/layout/DetailWindow.jsx";

/**
 * Porcentaje de asistencia del ciclo, un estudiante a la vez (RF-JOR-009).
 *
 * Igual que "Estado del dia": el endpoint exige estudiante y jornada, asi que
 * es una consulta puntual, no un listado. `elapsed_school_days` es la base
 * real del calculo (dias lectivos ya transcurridos desde que empezo la
 * matricula), y se muestra siempre para que el numero grande no se lea como
 * una cifra sin respaldo.
 *
 * Estudiante y jornada se eligen del catalogo. Pedirlos como "ID de estudiante"
 * y "ID de jornada" era pedir un UUID que solo existe en la base de datos:
 * nadie en el establecimiento lo conoce, y la unica forma de conseguirlo era
 * copiarlo de otra pantalla.
 */
export function AttendancePercentageProbe() {
  const students = useStudentCatalog();
  const shifts = useShiftCatalog();

  const [studentId, setStudentId] = useState("");
  const [shiftId, setShiftId] = useState("");
  // La fecha de corte por omision del backend es hoy; mostrarla puesta dice
  // CUAL es el corte en vez de dejar en blanco un dato que igual se aplica.
  const [asOfDate, setAsOfDate] = useState(todayInputValue);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const canSubmit = studentId !== "" && shiftId !== "" && !loading;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) return;

    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await attendanceService.attendancePercentage({
        student_id: studentId,
        shift_id: shiftId,
        ...(asOfDate ? { as_of_date: asOfDate } : null),
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
      subtitle="Requiere estudiante y jornada"
      sx={{ height: "100%" }}
      title="Porcentaje de asistencia"
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
              helperText="Hasta que dia se cuenta."
              label="Fecha de corte"
              onChange={(event) => setAsOfDate(event.target.value)}
              value={asOfDate}
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
            <Stack
              gap={1.5}
              sx={{ pt: 1, borderTop: "1px solid", borderColor: "divider" }}
            >
              <StatCard
                hint={`${result.present_days + result.late_days} de ${result.elapsed_school_days} dias lectivos transcurridos`}
                label="Porcentaje"
                value={
                  result.percentage == null ? "—" : `${result.percentage}%`
                }
              />
              <Box
                component="dl"
                sx={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 2,
                  m: 0,
                }}
              >
                <DetailField label="Presente" value={result.present_days} />
                <DetailField label="Tarde" value={result.late_days} />
              </Box>
            </Stack>
          ) : !error && !loading ? (
            <EmptyState message="Elija estudiante y jornada para consultar el porcentaje." />
          ) : null}
        </Stack>
      </Box>
    </SectionCard>
  );
}
