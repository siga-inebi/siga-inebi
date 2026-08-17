import { vi } from "vitest";

import { paginated } from "../fixtures/academics";

export const peopleServiceMock = {
  listPeople: vi.fn(),
};

export function resetPeopleServiceMock() {
  peopleServiceMock.listPeople.mockResolvedValue(paginated([]));
}
