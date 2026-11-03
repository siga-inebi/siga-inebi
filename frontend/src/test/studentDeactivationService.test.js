import { afterEach, expect, test, vi } from "vitest";
import { apiClient } from "@shared/api/apiClient.js";
import { studentsService } from "@students/studentsService.js";

afterEach(() => vi.restoreAllMocks());
test("desactiva por id interno con DELETE y acepta respuesta vacia", async () => {
  const del = vi.spyOn(apiClient, "del").mockResolvedValue(null);
  expect(await studentsService.deactivate(17)).toBeNull();
  expect(del).toHaveBeenCalledExactlyOnceWith("/students/17/");
});
