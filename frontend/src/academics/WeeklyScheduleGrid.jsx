import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { WEEKDAYS, blockLabel } from "./schedule.js";

/** Bloques presentes en las sesiones, por numero, cuando no se reciben aparte. */
function blocksFromSessions(sessions) {
  const byId = new Map();
  for (const session of sessions) {
    const block = session.schedule_block;
    if (block && !byId.has(block.public_id)) byId.set(block.public_id, block);
  }
  return [...byId.values()].sort(
    (left, right) =>
      (left.number ?? 0) - (right.number ?? 0) ||
      String(left.starts_on).localeCompare(String(right.starts_on))
  );
}

function DefaultSession({ session }) {
  return (
    <Stack gap={0.25}>
      <Typography sx={{ fontSize: "0.8125rem", fontWeight: 600 }}>
        {session.subject?.name ?? "Curso"}
      </Typography>
      {session.section?.name ? (
        <Typography color="text.secondary" sx={{ fontSize: "0.75rem" }}>
          {[session.section.grade?.name, session.section.name]
            .filter(Boolean)
            .join(" ")}
        </Typography>
      ) : null}
      {session.teacher?.name ? (
        <Typography color="text.secondary" sx={{ fontSize: "0.75rem" }}>
          {session.teacher.name}
        </Typography>
      ) : null}
      {session.classroom?.name ? (
        <Typography color="text.secondary" sx={{ fontSize: "0.75rem" }}>
          {session.classroom.name}
        </Typography>
      ) : null}
    </Stack>
  );
}

/**
 * Horario semanal como reja dias × bloques (S3, S4).
 *
 * Lo comparten "Mi horario" y la pestaña Horarios del ciclo: la misma clase se
 * lee igual en los dos lugares. Es solo presentacion; las reglas (choques,
 * docente vigente, carga) las valida el backend.
 *
 * @param {object} props
 * @param {Array} props.sessions Sesiones con `day_of_week` y `schedule_block`.
 * @param {Array} [props.blocks] Bloques de la jornada; si falta, salen de las sesiones.
 * @param {(session) => ReactNode} [props.renderSession]
 * @param {(day: number, block: object) => ReactNode} [props.renderEmpty]
 * @param {string} [props.caption] Nombre accesible de la tabla.
 */
export function WeeklyScheduleGrid({
  blocks,
  caption = "Horario semanal",
  renderEmpty,
  renderSession,
  sessions,
}) {
  const rows = blocks?.length ? blocks : blocksFromSessions(sessions);
  const usesWeekend = sessions.some((session) => session.day_of_week >= 6);
  const days = WEEKDAYS.filter(([day]) => day <= 5 || usesWeekend);

  const cell = new Map();
  for (const session of sessions) {
    const key = `${session.day_of_week}:${session.schedule_block?.public_id}`;
    cell.set(key, [...(cell.get(key) ?? []), session]);
  }

  return (
    <Box sx={{ overflowX: "auto" }}>
      <Box
        aria-label={caption}
        component="table"
        sx={{
          borderCollapse: "collapse",
          minWidth: "40rem",
          width: "100%",
          "& th, & td": {
            border: "1px solid",
            borderColor: "divider",
            p: 1,
            verticalAlign: "top",
            textAlign: "left",
          },
          "& th": {
            bgcolor: "action.hover",
            fontSize: "0.75rem",
            fontWeight: 600,
          },
        }}
      >
        <thead>
          <tr>
            <th scope="col">Bloque</th>
            {days.map(([day, label]) => (
              <th key={day} scope="col">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((block) => (
            <tr key={block.public_id}>
              <th scope="row" style={{ whiteSpace: "nowrap" }}>
                {blockLabel(block)}
              </th>
              {days.map(([day]) => {
                const items = cell.get(`${day}:${block.public_id}`) ?? [];
                return (
                  <td key={day}>
                    {items.length > 0 ? (
                      <Stack gap={1}>
                        {items.map((session) => (
                          <Box key={session.public_id}>
                            {renderSession ? (
                              renderSession(session)
                            ) : (
                              <DefaultSession session={session} />
                            )}
                          </Box>
                        ))}
                      </Stack>
                    ) : renderEmpty ? (
                      renderEmpty(day, block)
                    ) : null}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </Box>
    </Box>
  );
}
