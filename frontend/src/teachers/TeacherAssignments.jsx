import { useQuery } from "@tanstack/react-query";

import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { academicsService } from "@academics/academicsService.js";
import { sectionLabel } from "@academics/searchOptions.js";
import { queryKeys } from "@shared/api/queryKeys.js";
import { formatDate } from "@shared/utils/format.js";

/**
 * "Qué imparte" en la ficha del docente (docs/ux-ui.md AD4): sus asignaciones
 * vigentes, con los nombres que trae el listado del servidor.
 *
 * @param {object} props
 * @param {string} props.teacherId `public_id` del perfil docente.
 */
export function TeacherAssignments({ teacherId }) {
  const params = { teacher_id: teacherId, current: true };
  const query = useQuery({
    queryKey: queryKeys.academics.teachingAssignments(params),
    queryFn: () => academicsService.listTeachingAssignments(params),
  });
  const rows = query.data?.results ?? [];
  const more = (query.data?.count ?? 0) - rows.length;

  return (
    <Box aria-label="Qué imparte" component="section" sx={{ mt: 3 }}>
      <Typography
        component="h3"
        sx={{ fontSize: "0.9375rem", fontWeight: 600, mb: 1 }}
      >
        Qué imparte
      </Typography>
      {query.isPending ? (
        <Typography color="text.secondary" role="status" variant="body2">
          Consultando asignaciones…
        </Typography>
      ) : query.isError ? (
        <Alert severity="warning">{query.error.message}</Alert>
      ) : rows.length === 0 ? (
        <Typography color="text.secondary" variant="body2">
          Sin asignaciones vigentes.
        </Typography>
      ) : (
        <Stack component="ul" gap={0.75} sx={{ m: 0, pl: 2.5 }}>
          {rows.map((row) => (
            <Typography component="li" key={row.public_id} variant="body2">
              {[
                sectionLabel(row.section ?? {}),
                row.subject?.name ?? "Curso",
                `desde ${formatDate(row.starts_on)}`,
              ].join(" · ")}
            </Typography>
          ))}
          {more > 0 ? (
            <Typography color="text.secondary" component="li" variant="body2">
              y {more} más; véalas en Asignaciones docentes.
            </Typography>
          ) : null}
        </Stack>
      )}
    </Box>
  );
}
