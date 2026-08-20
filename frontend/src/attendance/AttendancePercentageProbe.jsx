import { useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import SearchIcon from "@mui/icons-material/Search";

import { attendanceService } from "@attendance/attendanceService.js";
import { StatCard } from "@ui/display/StatCard.jsx";
import { EmptyState } from "@ui/feedback/EmptyState.jsx";
import { FormTextField } from "@ui/forms/FormTextField.jsx";
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
 */
export function AttendancePercentageProbe() {
  const [studentId, setStudentId] = useState("");
  const [shiftId, setShiftId] = useState("");
  const [asOfDate, setAsOfDate] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const canSubmit =
    studentId.trim() !== "" && shiftId.trim() !== "" && !loading;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!canSubmit) return;

    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await attendanceService.attendancePercentage({
        student_id: studentId.trim(),
        shift_id: shiftId.trim(),
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
          <FormTextField
            label="ID de estudiante"
            onChange={(event) => setStudentId(event.target.value)}
            value={studentId}
          />
          <Stack direction={{ xs: "column", sm: "row" }} gap={2}>
            <FormTextField
              label="ID de jornada"
              onChange={(event) => setShiftId(event.target.value)}
              value={shiftId}
            />
            <FormTextField
              helperText="Opcional; por omision, hoy."
              label="Fecha de corte"
              onChange={(event) => setAsOfDate(event.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
              type="date"
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
            <EmptyState message="Completa estudiante y jornada para consultar el porcentaje." />
          ) : null}
        </Stack>
      </Box>
    </SectionCard>
  );
}
