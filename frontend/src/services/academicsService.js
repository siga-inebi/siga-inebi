import { apiClient } from "./apiClient.js";

const ROOT = "/academics";

/**
 * Tamano de pagina del backend (`REST_FRAMEWORK.PAGE_SIZE`). Los listados
 * responden `{ count, next, previous, results }`, asi que la interfaz necesita
 * este valor para calcular cuantas paginas hay.
 */
export const PAGE_SIZE = 25;

/**
 * Builds the query string the catalogue endpoints understand. Empty values are
 * dropped so `?page=1` never becomes `?page=1&include_inactive=false`.
 */
function withQuery(path, params) {
  const query = new URLSearchParams();

  for (const [key, value] of Object.entries(params || {})) {
    if (
      value === undefined ||
      value === null ||
      value === "" ||
      value === false
    ) {
      continue;
    }
    query.set(key, String(value));
  }

  const suffix = query.toString();
  return suffix ? `${path}?${suffix}` : path;
}

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
  updateCampus: (campusId, payload) =>
    apiClient.patch(`${ROOT}/campuses/${campusId}/`, payload),
  deactivateCampus: (campusId) =>
    apiClient.del(`${ROOT}/campuses/${campusId}/`),

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
  updateLevel: (levelId, payload) =>
    apiClient.patch(`${ROOT}/levels/${levelId}/`, payload),
  deactivateLevel: (levelId) => apiClient.del(`${ROOT}/levels/${levelId}/`),

  // grados: siempre se crean dentro de un nivel
  listLevelGrades: (levelId, params) =>
    apiClient.get(withQuery(`${ROOT}/levels/${levelId}/grades/`, params)),
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

  // ciclos escolares: el estado avanza draft -> active -> closed y no retrocede
  listCycles: (params) => apiClient.get(withQuery(`${ROOT}/cycles/`, params)),
  getCycle: (cycleId) => apiClient.get(`${ROOT}/cycles/${cycleId}/`),
  createCycle: (payload) => apiClient.post(`${ROOT}/cycles/`, payload),
  updateCycle: (cycleId, payload) =>
    apiClient.patch(`${ROOT}/cycles/${cycleId}/`, payload),
  changeCycleStatus: (cycleId, status) =>
    apiClient.post(`${ROOT}/cycles/${cycleId}/status/`, { status }),

  // oferta de grados: que grado se imparte en que jornada durante el ciclo
  listCycleOfferings: (cycleId, params) =>
    apiClient.get(withQuery(`${ROOT}/cycles/${cycleId}/offerings/`, params)),
  createOffering: (cycleId, payload) =>
    apiClient.post(`${ROOT}/cycles/${cycleId}/offerings/`, payload),
  getOffering: (offeringId) =>
    apiClient.get(`${ROOT}/offerings/${offeringId}/`),
  withdrawOffering: (offeringId) =>
    apiClient.del(`${ROOT}/offerings/${offeringId}/`),

  // secciones: siempre dentro de una oferta
  listOfferingSections: (offeringId, params) =>
    apiClient.get(
      withQuery(`${ROOT}/offerings/${offeringId}/sections/`, params)
    ),
  createSection: (offeringId, payload) =>
    apiClient.post(`${ROOT}/offerings/${offeringId}/sections/`, payload),
  getSection: (sectionId) => apiClient.get(`${ROOT}/sections/${sectionId}/`),
  updateSection: (sectionId, payload) =>
    apiClient.patch(`${ROOT}/sections/${sectionId}/`, payload),
  deactivateSection: (sectionId) =>
    apiClient.del(`${ROOT}/sections/${sectionId}/`),

  // plan de estudios del ciclo: acepta `grade` para ver el plan de un grado
  listCurriculum: (cycleId, params) =>
    apiClient.get(withQuery(`${ROOT}/cycles/${cycleId}/curriculum/`, params)),
  addCurriculumEntry: (cycleId, payload) =>
    apiClient.post(`${ROOT}/cycles/${cycleId}/curriculum/`, payload),
  updateCurriculumEntry: (entryId, payload) =>
    apiClient.patch(`${ROOT}/curriculum/${entryId}/`, payload),
  removeCurriculumEntry: (entryId) =>
    apiClient.del(`${ROOT}/curriculum/${entryId}/`),

  // asignacion docente: cerrar no borra, deja la fila como historia
  listSectionAssignments: (sectionId, params) =>
    apiClient.get(
      withQuery(`${ROOT}/sections/${sectionId}/assignments/`, params)
    ),
  assignTeacher: (sectionId, payload) =>
    apiClient.post(`${ROOT}/sections/${sectionId}/assignments/`, payload),
  endAssignmentOn: (assignmentId, endsOn) =>
    apiClient.patch(`${ROOT}/assignments/${assignmentId}/`, {
      ends_on: endsOn,
    }),
  endAssignment: (assignmentId) =>
    apiClient.del(`${ROOT}/assignments/${assignmentId}/`),
};
