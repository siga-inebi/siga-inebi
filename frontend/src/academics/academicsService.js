import { apiClient } from "@shared/api/apiClient.js";
import { withQuery } from "@shared/api/query.js";

const ROOT = "/academics";

/**
 * Tamano de pagina del backend (`REST_FRAMEWORK.PAGE_SIZE`). Los listados
 * responden `{ count, next, previous, results }`, asi que la interfaz necesita
 * este valor para calcular cuantas paginas hay.
 */
export const PAGE_SIZE = 25;

/**
 * Catalogo academico completo: la estructura institucional (sedes y jornadas) y
 * la estructura academica (niveles, grados, cursos y su vinculo).
 *
 * Una funcion por endpoint publicado en `apps.academics`. `del` es baja logica
 * (RF-EST-012): el registro queda inactivo y sigue listandose con
 * `include_inactive=true`.
 */
export const academicsService = {
  // sedes
  listCampuses: (params) =>
    apiClient.get(withQuery(`${ROOT}/campuses/`, params)),
  getCampus: (campusId) => apiClient.get(`${ROOT}/campuses/${campusId}/`),
  createCampus: (payload) => apiClient.post(`${ROOT}/campuses/`, payload),
  /** Siguiente codigo de sede libre. Ver `studentsService.nextCode`. */
  nextCampusCode: () =>
    apiClient.get(`${ROOT}/campuses/next-code/`).then((body) => body.code),
  updateCampus: (campusId, payload) =>
    apiClient.patch(`${ROOT}/campuses/${campusId}/`, payload),
  deactivateCampus: (campusId) =>
    apiClient.del(`${ROOT}/campuses/${campusId}/`),

  // aulas: espacios fisicos asociados a una sede (RF-AUL-001)
  listClassrooms: (params) =>
    apiClient.get(withQuery(`${ROOT}/classrooms/`, params)),
  getClassroom: (classroomId) =>
    apiClient.get(`${ROOT}/classrooms/${classroomId}/`),
  createClassroom: (payload) => apiClient.post(`${ROOT}/classrooms/`, payload),
  updateClassroom: (classroomId, payload) =>
    apiClient.patch(`${ROOT}/classrooms/${classroomId}/`, payload),
  deactivateClassroom: (classroomId) =>
    apiClient.del(`${ROOT}/classrooms/${classroomId}/`),

  // jornadas: siempre se crean dentro de una sede
  listCampusShifts: (campusId, params) =>
    apiClient.get(withQuery(`${ROOT}/campuses/${campusId}/shifts/`, params)),
  createShift: (campusId, payload) =>
    apiClient.post(`${ROOT}/campuses/${campusId}/shifts/`, payload),
  getShift: (shiftId) => apiClient.get(`${ROOT}/shifts/${shiftId}/`),
  updateShift: (shiftId, payload) =>
    apiClient.patch(`${ROOT}/shifts/${shiftId}/`, payload),
  deactivateShift: (shiftId) => apiClient.del(`${ROOT}/shifts/${shiftId}/`),

  // niveles
  listLevels: (params) => apiClient.get(withQuery(`${ROOT}/levels/`, params)),
  getLevel: (levelId) => apiClient.get(`${ROOT}/levels/${levelId}/`),
  createLevel: (payload) => apiClient.post(`${ROOT}/levels/`, payload),
  /** Siguiente codigo de nivel libre. */
  nextLevelCode: () =>
    apiClient.get(`${ROOT}/levels/next-code/`).then((body) => body.code),
  updateLevel: (levelId, payload) =>
    apiClient.patch(`${ROOT}/levels/${levelId}/`, payload),
  deactivateLevel: (levelId) => apiClient.del(`${ROOT}/levels/${levelId}/`),

  // grados: siempre se crean dentro de un nivel
  listLevelGrades: (levelId, params) =>
    apiClient.get(withQuery(`${ROOT}/levels/${levelId}/grades/`, params)),
  /** Siguiente codigo de grado, derivado del codigo de su nivel ("BAS1"). */
  nextGradeCode: (levelId) =>
    apiClient
      .get(`${ROOT}/levels/${levelId}/grades/next-code/`)
      .then((body) => body.code),
  createGrade: (levelId, payload) =>
    apiClient.post(`${ROOT}/levels/${levelId}/grades/`, payload),
  getGrade: (gradeId) => apiClient.get(`${ROOT}/grades/${gradeId}/`),
  updateGrade: (gradeId, payload) =>
    apiClient.patch(`${ROOT}/grades/${gradeId}/`, payload),
  deactivateGrade: (gradeId) => apiClient.del(`${ROOT}/grades/${gradeId}/`),

  // cursos
  listSubjects: (params) =>
    apiClient.get(withQuery(`${ROOT}/subjects/`, params)),
  getSubject: (subjectId) => apiClient.get(`${ROOT}/subjects/${subjectId}/`),
  createSubject: (payload) => apiClient.post(`${ROOT}/subjects/`, payload),
  updateSubject: (subjectId, payload) =>
    apiClient.patch(`${ROOT}/subjects/${subjectId}/`, payload),
  deactivateSubject: (subjectId) =>
    apiClient.del(`${ROOT}/subjects/${subjectId}/`),

  // vinculo curso <-> nivel: el plan de estudios del nivel
  listLevelSubjects: (levelId, params) =>
    apiClient.get(withQuery(`${ROOT}/levels/${levelId}/subjects/`, params)),
  linkSubjectToLevel: (levelId, payload) =>
    apiClient.post(`${ROOT}/levels/${levelId}/subjects/`, payload),
  updateLevelSubject: (levelId, subjectId, payload) =>
    apiClient.patch(
      `${ROOT}/levels/${levelId}/subjects/${subjectId}/`,
      payload
    ),
  unlinkSubjectFromLevel: (levelId, subjectId) =>
    apiClient.del(`${ROOT}/levels/${levelId}/subjects/${subjectId}/`),

  // secciones: el listado global es plano y trae grado y jornada anidados, que
  // es justo lo que necesita un selector para etiquetarse sin pedir mas datos.
  listSections: (params) =>
    apiClient.get(withQuery(`${ROOT}/sections/`, params)),

  // asignaciones docentes
  //
  // No hay endpoint de "asignaciones vigentes": el listado es el historial, y la
  // vigencia se lee de `ends_on`. Reasignar no edita, cierra y abre.
  listTeachingAssignmentHistory: (params) =>
    apiClient.get(withQuery(`${ROOT}/teaching-assignments/history/`, params)),
  createTeachingAssignment: (payload) =>
    apiClient.post(`${ROOT}/teaching-assignments/`, payload),
  reassignTeachingAssignment: (assignmentId, payload) =>
    apiClient.post(
      `${ROOT}/teaching-assignments/${assignmentId}/reassignments/`,
      payload
    ),
};
