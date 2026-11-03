import { studentOption } from "@shared/catalogs/academicCatalogs.js";
import { CATALOG } from "@shared/api/queryKeys.js";
import { studentsService } from "@students/studentsService.js";

/**
 * Selector de estudiante con búsqueda en el servidor (docs/ux-ui.md 1.3): las
 * pantallas de asistencia ya no descargan el padrón completo para llenar un
 * desplegable ni para nombrar las filas.
 */
export const STUDENT_SEARCH = Object.freeze({
  name: CATALOG.students,
  fetchPage: (params) => studentsService.listPage(params),
  mapResult: studentOption,
});

/** "Ana Pérez · EST-1" a partir de la referencia `student` de una fila. */
export function studentLabel(student) {
  return [student?.full_name, student?.student_code]
    .filter(Boolean)
    .join(" · ");
}

/** "1:05:09" o "4:09": lo que falta para que venza el turno de captura. */
export function formatRemaining(milliseconds) {
  const total = Math.max(0, Math.floor(milliseconds / 1000));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = String(total % 60).padStart(2, "0");
  return hours > 0
    ? `${hours}:${String(minutes).padStart(2, "0")}:${seconds}`
    : `${minutes}:${seconds}`;
}
