import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { enrolmentsService } from "@enrolments/enrolmentsService.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { DetailField } from "@ui/layout/DetailWindow.jsx";

/** Datos del servidor: no calcula vacantes ni sustituye la validación al guardar. */
export function SectionOccupancyNotice({ cycleId, sectionId, busy = false }) {
  const params = { academic_cycle_id: cycleId, section_id: sectionId };
  const ready = Boolean(cycleId && sectionId);
  const query = useQuery({
    queryKey: queryKeys.enrolments.occupancy(params),
    queryFn: async () => {
      const page = await enrolmentsService.listSectionOccupancy(params);
      return (
        page.results.find(
          (row) =>
            row.public_id === sectionId && row.academic_cycle_id === cycleId
        ) ?? null
      );
    },
    enabled: ready && !busy,
    staleTime: 0,
    retry: false,
    refetchOnMount: "always",
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  return (
    <Stack aria-label="Cupo de la sección" component="section" gap={1.5}>
      <Typography component="h3" variant="subtitle2">
        Cupo de la sección
      </Typography>
      {!ready ? (
        <Typography color="text.secondary" variant="body2">
          Seleccione una sección para consultar su cupo.
        </Typography>
      ) : busy ? (
        <Typography role="status" variant="body2">
          El cupo se actualizará al terminar la operación.
        </Typography>
      ) : query.isPending || query.isFetching ? (
        <Stack direction="row" gap={1} alignItems="center" role="status">
          <CircularProgress size={18} />
          <Typography variant="body2">Consultando cupo…</Typography>
        </Stack>
      ) : query.isError ? (
        <Alert severity="warning">
          No se pudo consultar el cupo. {query.error.message}
        </Alert>
      ) : !query.data ? (
        <Alert severity="warning">
          No hay información de cupo para la sección seleccionada.
        </Alert>
      ) : (
        <>
          <Box
            component="dl"
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" },
              gap: 2,
              m: 0,
            }}
          >
            <DetailField
              label="Cupo declarado"
              value={
                query.data.capacity === 0
                  ? "Sin límite declarado"
                  : query.data.capacity
              }
            />
            <DetailField
              label="Plazas ocupadas"
              value={query.data.occupied_seats}
            />
            <DetailField
              label="Vacantes disponibles"
              value={
                query.data.available_seats === null
                  ? "Sin límite declarado"
                  : query.data.available_seats
              }
            />
          </Box>
          <Alert
            severity={query.data.available_seats === 0 ? "warning" : "info"}
          >
            {query.data.available_seats === 0 ? "Sección sin vacantes. " : ""}
            La disponibilidad puede cambiar y se confirma al guardar.
          </Alert>
        </>
      )}
      {ready ? (
        <Button
          disabled={busy || query.isFetching}
          onClick={() => query.refetch()}
          size="small"
          sx={{ alignSelf: "flex-start" }}
        >
          {query.isError ? "Reintentar cupo" : "Actualizar cupo"}
        </Button>
      ) : null}
    </Stack>
  );
}
