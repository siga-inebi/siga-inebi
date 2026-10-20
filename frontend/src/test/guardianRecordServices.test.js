import { vi } from "vitest";
import { apiClient } from "@shared/api/apiClient.js";
import { guardiansService } from "@guardians/guardiansService.js";

test("G4 usa el encargado concreto, página y búsqueda; vincula por UUID", async () => {
  const get = vi.spyOn(apiClient, "get").mockResolvedValue({ results: [] });
  const post = vi.spyOn(apiClient, "post").mockResolvedValue({});
  await guardiansService.linkedStudents(17, { page: 2 });
  expect(get).toHaveBeenLastCalledWith(
    "/students/guardians/17/students/?page=2"
  );
  await guardiansService.studentCandidates(17, { search: "Ana Lopez" });
  expect(get).toHaveBeenLastCalledWith(
    "/students/guardians/17/student-candidates/?search=Ana+Lopez"
  );
  const payload = {
    student_public_id: "student-27",
    relationship_label: "Familiar",
  };
  await guardiansService.linkStudent(17, payload);
  expect(post).toHaveBeenCalledExactlyOnceWith(
    "/students/guardians/17/students/",
    payload
  );
});
