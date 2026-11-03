import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { MutedCell } from "@ui/table/cells.jsx";

/** Nombre y código del estudiante de una fila (`row.student`). */
export function StudentCell({ student }) {
  if (!student) return <MutedCell>Sin dato</MutedCell>;
  return (
    <Stack>
      <span>{student.full_name}</span>
      <Typography color="text.secondary" variant="caption">
        {student.student_code}
      </Typography>
    </Stack>
  );
}
