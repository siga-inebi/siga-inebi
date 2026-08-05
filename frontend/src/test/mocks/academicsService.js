import { vi } from "vitest";

import { paginated } from "../fixtures/academics";

const LIST_METHODS = [
  "listCampuses",
  "listCampusShifts",
  "listLevels",
  "listLevelGrades",
  "listSubjects",
  "listLevelSubjects",
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

export const academicsServiceMock = Object.fromEntries(
  [...LIST_METHODS, ...WRITE_METHODS, ...DELETE_METHODS, ...DETAIL_METHODS].map(
    (name) => [name, vi.fn()]
  )
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
}
