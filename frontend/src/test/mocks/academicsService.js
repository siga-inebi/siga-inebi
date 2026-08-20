import { vi } from "vitest";

import { paginated } from "../fixtures/academics";

const LIST_METHODS = [
  "listCampuses",
  "listCampusShifts",
  "listLevels",
  "listLevelGrades",
  "listSubjects",
  "listSections",
  "listLevelSubjects",
  "listTeachingAssignmentHistory",
];

const WRITE_METHODS = [
  "createCampus",
  "updateCampus",
  "createShift",
  "updateShift",
  "createLevel",
  "updateLevel",
  "createGrade",
  "updateGrade",
  "createSubject",
  "updateSubject",
  "linkSubjectToLevel",
  "updateLevelSubject",
  "createTeachingAssignment",
  "reassignTeachingAssignment",
];

const DELETE_METHODS = [
  "deactivateCampus",
  "deactivateShift",
  "deactivateLevel",
  "deactivateGrade",
  "deactivateSubject",
  "unlinkSubjectFromLevel",
];

const DETAIL_METHODS = [
  "getCampus",
  "getShift",
  "getLevel",
  "getGrade",
  "getSubject",
];

/**
 * Sugerencias de codigo. Devuelven texto, no una pagina.
 *
 * Por defecto resuelven a vacio: la pantalla debe abrir el formulario igual si
 * la sugerencia no llega, porque el backend genera el codigo de todos modos.
 */
const SUGGESTION_METHODS = ["nextCampusCode", "nextLevelCode", "nextGradeCode"];

export const academicsServiceMock = Object.fromEntries(
  [
    ...LIST_METHODS,
    ...WRITE_METHODS,
    ...DELETE_METHODS,
    ...DETAIL_METHODS,
    ...SUGGESTION_METHODS,
  ].map((name) => [name, vi.fn()])
);

/**
 * Deja el doble en su estado por defecto: listados vacios y escrituras que
 * resuelven. `vi.clearAllMocks` solo limpia las llamadas, no lo que cada
 * prueba haya configurado, asi que cada suite llama a esto en `beforeEach`.
 */
export function resetAcademicsServiceMock() {
  for (const name of LIST_METHODS) {
    academicsServiceMock[name].mockResolvedValue(paginated([]));
  }
  for (const name of WRITE_METHODS) {
    academicsServiceMock[name].mockResolvedValue({});
  }
  for (const name of DELETE_METHODS) {
    academicsServiceMock[name].mockResolvedValue(null);
  }
  for (const name of DETAIL_METHODS) {
    academicsServiceMock[name].mockResolvedValue({});
  }
  for (const name of SUGGESTION_METHODS) {
    academicsServiceMock[name].mockResolvedValue("");
  }
}
