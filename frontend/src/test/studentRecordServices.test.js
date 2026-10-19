import { vi } from "vitest";
import { apiClient } from "@shared/api/apiClient.js";
import { studentsService } from "@students/studentsService.js";

const STUDENT = "11111111-1111-1111-1111-111111111111";

afterEach(() => vi.restoreAllMocks());

test.each([
  [
    "listGuardianRelations",
    `/students/guardian-relations/?page=2&student_id=${STUDENT}`,
  ],
  ["listHealthNotes", `/students/${STUDENT}/health-notes/?page=2`],
  ["listObservations", `/students/${STUDENT}/observations/?page=2`],
  ["listEmergencyContacts", `/students/${STUDENT}/emergency-contacts/?page=2`],
])(
  "%s preserves pagination and requests only the selected student's page",
  async (method, url) => {
    const page = {
      count: 26,
      results: [{ public_id: "record-26" }],
      next: null,
      previous: "?page=1",
    };
    vi.spyOn(apiClient, "get").mockResolvedValue(page);

    const result = await studentsService[method](STUDENT, { page: 2 });

    expect(apiClient.get).toHaveBeenCalledWith(url);
    expect(apiClient.get).toHaveBeenCalledTimes(1);
    expect(result).toBe(page);
  }
);
