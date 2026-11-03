import { vi } from "vitest";

import { paginated } from "../fixtures/academics.js";

const LIST_METHODS = ["listPeople"];
const WRITE_METHODS = ["createPerson", "updatePerson"];
const DELETE_METHODS = ["deactivatePerson"];
const DETAIL_METHODS = ["getPerson"];

export const peopleServiceMock = Object.fromEntries(
  [...LIST_METHODS, ...WRITE_METHODS, ...DELETE_METHODS, ...DETAIL_METHODS].map(
    (name) => [name, vi.fn()]
  )
);

/**
 * Same reset contract as `resetAcademicsServiceMock`: listados vacios y
 * escrituras que resuelven, para que cada prueba solo configure lo que le
 * importa.
 */
export function resetPeopleServiceMock() {
  for (const name of LIST_METHODS) {
    peopleServiceMock[name].mockResolvedValue(paginated([]));
  }
  for (const name of WRITE_METHODS) {
    peopleServiceMock[name].mockResolvedValue({});
  }
  for (const name of DELETE_METHODS) {
    peopleServiceMock[name].mockResolvedValue(null);
  }
  for (const name of DETAIL_METHODS) {
    peopleServiceMock[name].mockResolvedValue({});
  }
}
