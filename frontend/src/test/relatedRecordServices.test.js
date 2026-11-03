import { afterEach, expect, test, vi } from "vitest";
import { apiClient } from "@shared/api/apiClient.js";
import { studentsService } from "@students/studentsService.js";

afterEach(() => vi.restoreAllMocks());

test.each([
  ["HealthNote", "health-notes", { content: "Salud sintetica" }],
  ["Observation", "observations", { description: "Observacion sintetica" }],
  ["EmergencyContact", "emergency-contacts", { name: "Contacto sintetico" }],
])(
  "edicion y desactivacion %s conservan rutas y verbos",
  async (name, path, payload) => {
    const patch = vi.spyOn(apiClient, "patch").mockResolvedValue({});
    const del = vi.spyOn(apiClient, "del").mockResolvedValue(null);
    await studentsService[`update${name}`]("record-demo", payload);
    await studentsService[`deactivate${name}`]("record-demo");
    expect(patch).toHaveBeenCalledExactlyOnceWith(
      `/students/${path}/record-demo/`,
      payload
    );
    expect(del).toHaveBeenCalledExactlyOnceWith(
      `/students/${path}/record-demo/`
    );
  }
);
