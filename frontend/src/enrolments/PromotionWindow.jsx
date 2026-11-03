import { useEffect, useState } from "react";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { enrolmentsService } from "@enrolments/enrolmentsService.js";
import { DetailField } from "@ui/layout/DetailWindow.jsx";
import { FloatingWindow } from "@ui/layout/FloatingWindow.jsx";
import { WINDOW_WIDTH } from "@ui/layout/windowWidth.js";

const PROGRESSION_LABEL = {
  promoted: "Promovido",
  repeating: "No promovido · Repitencia",
  graduated: "Graduación",
};

/** Presenta la decisión del servidor; no calcula notas ni crea matrículas. */
export function PromotionWindow({ enrolment, context = [], onClose }) {
  const [attempt, setAttempt] = useState(0);
  const [query, setQuery] = useState({ loading: true });
  const enrolmentId = enrolment.public_id;

  useEffect(() => {
    let current = true;
    enrolmentsService.getPromotion(enrolmentId).then(
      (data) => {
        if (current) setQuery({ enrolmentId, data });
      },
      (error) => {
        if (current) setQuery({ enrolmentId, error: error.message });
      }
    );
    return () => {
      current = false;
    };
  }, [enrolmentId, attempt]);

  const loading = query.loading || query.enrolmentId !== enrolmentId;
  const data = loading ? null : query.data;

  return (
    <FloatingWindow
      busy={loading}
      description="Consulta del resultado académico y del grado elegible para el siguiente ciclo. Esta consulta no crea ni modifica matrículas."
      footer={<Button onClick={onClose}>Cerrar</Button>}
      onClose={onClose}
      open
      title="Consultar promoción"
      width={WINDOW_WIDTH.medium}
    >
      <Stack gap={2}>
        <Box
          component="dl"
          sx={{
            display: "grid",
            gridTemplateColumns: { sm: "1fr 1fr" },
            gap: 2,
            m: 0,
          }}
        >
          {context.map((field) => (
            <DetailField key={field.label} {...field} />
          ))}
        </Box>
        {loading ? (
          <Stack alignItems="center" gap={1} role="status">
            <CircularProgress size={24} />
            <Typography>Consultando promoción…</Typography>
          </Stack>
        ) : query.error ? (
          <Alert
            action={
              <Button
                color="inherit"
                onClick={() => {
                  setQuery({ loading: true });
                  setAttempt((value) => value + 1);
                }}
              >
                Reintentar
              </Button>
            }
            severity="error"
          >
            {query.error}
          </Alert>
        ) : null}
        {data ? (
          <>
            <Typography component="h3" variant="h5">
              {PROGRESSION_LABEL[data.progression]}
            </Typography>
            <Box component="dl" sx={{ m: 0 }}>
              <DetailField
                label="Grado elegible"
                value={
                  data.eligible_grade_name ??
                  "Sin grado siguiente por graduación"
                }
              />
              <DetailField
                label="Subáreas evaluadas"
                value={data.total_subjects}
              />
            </Box>
            <Alert
              severity={data.result_source === "frozen" ? "info" : "warning"}
            >
              {data.result_source === "frozen"
                ? "Resultado congelado al cierre del ciclo."
                : "Resultado calculado con las notas actuales. No hay un resultado congelado; puede cambiar al registrar o corregir notas."}
            </Alert>
            {data.total_subjects === 0 ? (
              <Alert severity="warning">
                El servidor no reporta subáreas evaluadas. Revise el plan de
                estudios y los resultados antes de tramitar la reinscripción.
              </Alert>
            ) : null}
            {data.failed_subjects.length > 0 ? (
              <Box>
                <Typography component="h4" variant="subtitle2">
                  Subáreas que impiden la promoción
                </Typography>
                <Box component="ul" sx={{ my: 1, pl: 3 }}>
                  {data.failed_subjects.map((subject, index) => (
                    <li key={`${index}-${subject}`}>{subject}</li>
                  ))}
                </Box>
                <Typography color="text.secondary" variant="body2">
                  Incluye subáreas reprobadas o sin calificar según el resultado
                  del servidor.
                </Typography>
              </Box>
            ) : null}
          </>
        ) : null}
      </Stack>
    </FloatingWindow>
  );
}
