import { expect, test, vi } from "vitest";
import { documentsService } from "@documents/documentsService.js";
import { apiClient } from "@shared/api/apiClient.js";

test("availability uses the bounded institutional endpoint without pagination or template downloads", async () => {
  const payload = [
    { code: "study_certificate", active_template: null, uses_fallback: true },
  ];
  const get = vi.spyOn(apiClient, "get").mockResolvedValue(payload);
  try {
    expect(await documentsService.listTemplateIssuanceUses()).toBe(payload);
    expect(get).toHaveBeenCalledExactlyOnceWith(
      "/documents/templates/issuance-uses/"
    );
  } finally {
    get.mockRestore();
  }
});
