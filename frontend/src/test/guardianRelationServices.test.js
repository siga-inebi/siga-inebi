import { afterEach, expect, test, vi } from "vitest";
import { apiClient } from "@shared/api/apiClient.js";
import { studentsService } from "@students/studentsService.js";

afterEach(() => vi.restoreAllMocks());

test("contratos de edicion, principal, finalizacion y pagina de reemplazos", async () => {
  const patch = vi.spyOn(apiClient, "patch").mockResolvedValue({});
  const post = vi.spyOn(apiClient, "post").mockResolvedValue({});
  const get = vi
    .spyOn(apiClient, "get")
    .mockResolvedValue({ count: 26, results: [] });
  await studentsService.updateGuardianRelation(11, {
    relationship_label: "Tutor",
  });
  expect(patch).toHaveBeenCalledWith("/students/guardian-relations/11/", {
    relationship_label: "Tutor",
  });
  await studentsService.makeGuardianRelationPrimary(11);
  expect(post).toHaveBeenCalledWith(
    "/students/guardian-relations/11/make-primary/",
    {}
  );
  await studentsService.endGuardianRelation(11, { replacement_relation: 12 });
  expect(post).toHaveBeenCalledWith("/students/guardian-relations/11/end/", {
    replacement_relation: 12,
  });
  await studentsService.listRecordGuardians("student-demo", {
    page: 2,
    replacement_for: 11,
  });
  expect(get).toHaveBeenCalledExactlyOnceWith(
    "/students/records/student-demo/guardians/?page=2&replacement_for=11"
  );
});
