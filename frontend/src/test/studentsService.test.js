import { beforeEach, describe, expect, test, vi } from "vitest";

import { apiClient } from "../services/apiClient.js";
import { studentsService } from "../services/studentsService.js";

const STUDENT = "11111111-1111-1111-1111-111111111111";
const CONTACT = "22222222-2222-2222-2222-222222222222";
const RELATION = "33333333-3333-3333-3333-333333333333";

describe("studentsService", () => {
  beforeEach(() => {
    vi.spyOn(apiClient, "get").mockResolvedValue({ count: 0, results: [] });
    vi.spyOn(apiClient, "post").mockResolvedValue({});
    vi.spyOn(apiClient, "patch").mockResolvedValue({});
    vi.spyOn(apiClient, "del").mockResolvedValue(null);
  });

  test("fetches guardian options without any query string", async () => {
    await studentsService.listGuardianOptions();

    expect(apiClient.get).toHaveBeenCalledWith("/students/guardians/options/");
  });

  test("nests emergency contact creation and listing under the student", async () => {
    await studentsService.listEmergencyContacts(STUDENT, { page: 2 });
    expect(apiClient.get).toHaveBeenCalledWith(
      `/students/${STUDENT}/emergency-contacts/?page=2`
    );

    await studentsService.createEmergencyContact(STUDENT, { name: "Maria" });
    expect(apiClient.post).toHaveBeenCalledWith(
      `/students/${STUDENT}/emergency-contacts/`,
      { name: "Maria" }
    );
  });

  test("addresses emergency contact detail flat, by its own id", async () => {
    await studentsService.updateEmergencyContact(CONTACT, { name: "Nuevo" });
    expect(apiClient.patch).toHaveBeenCalledWith(
      `/students/emergency-contacts/${CONTACT}/`,
      { name: "Nuevo" }
    );

    await studentsService.deactivateEmergencyContact(CONTACT);
    expect(apiClient.del).toHaveBeenCalledWith(
      `/students/emergency-contacts/${CONTACT}/`
    );
  });

  test("nests guardian relation creation and listing under the student", async () => {
    await studentsService.listStudentGuardianRelations(STUDENT, {
      include_inactive: true,
    });
    expect(apiClient.get).toHaveBeenCalledWith(
      `/students/${STUDENT}/guardian-relations/?include_inactive=true`
    );

    await studentsService.createStudentGuardianRelation(STUDENT, {
      guardian_id: "guardian-1",
    });
    expect(apiClient.post).toHaveBeenCalledWith(
      `/students/${STUDENT}/guardian-relations/`,
      { guardian_id: "guardian-1" }
    );
  });

  test("addresses guardian relation detail flat, by its own id", async () => {
    await studentsService.updateStudentGuardianRelation(RELATION, {
      is_primary: true,
    });
    expect(apiClient.patch).toHaveBeenCalledWith(
      `/students/guardian-relations/${RELATION}/`,
      { is_primary: true }
    );

    await studentsService.endStudentGuardianRelation(RELATION);
    expect(apiClient.del).toHaveBeenCalledWith(
      `/students/guardian-relations/${RELATION}/`
    );
  });
});
