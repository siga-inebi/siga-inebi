import { apiClient } from "../services/apiClient.js";

describe("apiClient", () => {
  test("includes credentials in requests", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ ok: true }),
    });

    await apiClient.get("/health/");

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "/api/v1/health/",
      expect.objectContaining({ credentials: "include" })
    );
  });

  test("sends csrf token on write requests", async () => {
    document.cookie = "csrftoken=test-token";
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ ok: true }),
    });

    await apiClient.post("/auth/login/", {
      username: "admin",
      password: "admin",
    });

    const [, options] = globalThis.fetch.mock.calls[0];
    expect(options.headers.get("X-CSRFToken")).toBe("test-token");
  });

  test("handles 401 responses", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ detail: "No autenticado." }),
    });

    await expect(apiClient.get("/auth/me/")).rejects.toMatchObject({
      status: 401,
      message: "No autenticado.",
    });
  });

  test("handles 403 responses", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ detail: "Sin permiso." }),
    });

    await expect(apiClient.get("/auth/me/")).rejects.toMatchObject({
      status: 403,
      message: "Sin permiso.",
    });
  });

  test("handles validation responses", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ error: { detail: "Datos invalidos." } }),
    });

    await expect(apiClient.post("/auth/login/", {})).rejects.toMatchObject({
      status: 422,
      message: "Datos invalidos.",
    });
  });

  test("handles server responses", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ detail: "Error interno." }),
    });

    await expect(apiClient.get("/health/")).rejects.toMatchObject({
      status: 500,
      message: "Error interno.",
    });
  });
});
