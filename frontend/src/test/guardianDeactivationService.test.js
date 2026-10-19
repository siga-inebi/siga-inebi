import { vi } from "vitest";

import { guardiansService } from "@guardians/guardiansService.js";
import { apiClient } from "@shared/api/apiClient.js";

test("desactivar encargado usa DELETE sin cuerpo con su identificador entero", async () => {
  const request = vi.spyOn(apiClient, "del").mockResolvedValue(null);
  await guardiansService.deactivate(632);
  expect(request).toHaveBeenCalledExactlyOnceWith("/students/guardians/632/");
});
