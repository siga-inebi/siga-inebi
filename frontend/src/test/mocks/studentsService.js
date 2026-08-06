import { vi } from "vitest";

import { paginated } from "../fixtures/academics.js";

const LIST_METHODS = ["listEmergencyContacts", "listStudentGuardianRelations"];

const WRITE_METHODS = [
  "createEmergencyContact",
  "updateEmergencyContact",
  "createStudentGuardianRelation",
  "updateStudentGuardianRelation",
];

const DELETE_METHODS = [
  "deactivateEmergencyContact",
  "endStudentGuardianRelation",
];

// Unpaginated: GuardianOptionListView answers a plain array.
const OPTION_METHODS = ["listGuardianOptions"];

export const studentsServiceMock = Object.fromEntries(
  [...LIST_METHODS, ...WRITE_METHODS, ...DELETE_METHODS, ...OPTION_METHODS].map(
    (name) => [name, vi.fn()]
  )
);

export function resetStudentsServiceMock() {
  for (const name of LIST_METHODS) {
    studentsServiceMock[name].mockResolvedValue(paginated([]));
  }
  for (const name of WRITE_METHODS) {
    studentsServiceMock[name].mockResolvedValue({});
  }
  for (const name of DELETE_METHODS) {
    studentsServiceMock[name].mockResolvedValue(null);
  }
  for (const name of OPTION_METHODS) {
    studentsServiceMock[name].mockResolvedValue([]);
  }
}
