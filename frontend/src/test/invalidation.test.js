import { QueryClient } from "@tanstack/react-query";
import { afterEach, describe, expect, test, vi } from "vitest";

import { apiClient, MUTATION_EVENT } from "@shared/api/apiClient.js";
import {
  keysForMutation,
  registerMutationInvalidation,
} from "@shared/api/invalidation.js";

function jsonResponse(body, { status = 200 } = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("toda mutacion invalida lo que muestra (ux-ui 1.2.3)", () => {
  let unregister = () => {};

  afterEach(() => {
    unregister();
  });

  test("cada ruta de escritura sabe que keys toca", () => {
    expect(keysForMutation("/teachers/abc/")).toEqual(
      expect.arrayContaining([
        ["teachers"],
        ["catalog", "teachers"],
        ["search", "teachers"],
        ["dashboard"],
      ])
    );
    expect(keysForMutation("/students/guardians/")).toEqual(
      expect.arrayContaining([["guardians"], ["students"]])
    );
    expect(keysForMutation("/identity/accounts/x/unlock/")).toEqual([
      ["identity"],
    ]);
    expect(keysForMutation("/auth/logout/")).toEqual([]);
    // Ruta sin regla: se invalida todo antes que dejar datos viejos.
    expect(keysForMutation("/desconocido/")).toBeNull();
  });

  test("apiClient avisa despues de una escritura exitosa y no despues de leer", async () => {
    const listener = vi.fn();
    window.addEventListener(MUTATION_EVENT, listener);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ ok: true }))
    );

    await apiClient.get("/teachers/");
    expect(listener).not.toHaveBeenCalled();

    await apiClient.post("/teachers/", { name: "x" });
    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener.mock.calls[0][0].detail).toEqual({
      method: "POST",
      path: "/teachers/",
    });
    window.removeEventListener(MUTATION_EVENT, listener);
  });

  test("una escritura rechazada no invalida nada", async () => {
    const listener = vi.fn();
    window.addEventListener(MUTATION_EVENT, listener);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({ error: { detail: "no" } }, { status: 400 })
      )
    );

    await expect(apiClient.post("/teachers/", {})).rejects.toThrow("no");
    expect(listener).not.toHaveBeenCalled();
    window.removeEventListener(MUTATION_EVENT, listener);
  });

  test("el registro global invalida las keys de la ruta escrita", async () => {
    const client = new QueryClient();
    const spy = vi.spyOn(client, "invalidateQueries");
    unregister = registerMutationInvalidation(client);

    window.dispatchEvent(
      new CustomEvent(MUTATION_EVENT, {
        detail: { method: "POST", path: "/teachers/" },
      })
    );

    expect(spy).toHaveBeenCalledWith({ queryKey: ["teachers"] });
    expect(spy).toHaveBeenCalledWith({ queryKey: ["catalog", "teachers"] });
  });

  test("una query de catalogo queda vieja tras crear un registro de su dominio", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { staleTime: 60_000 } },
    });
    unregister = registerMutationInvalidation(client);
    client.setQueryData(["catalog", "teachers", 0], [{ value: "1" }]);
    expect(client.getQueryState(["catalog", "teachers", 0]).isInvalidated).toBe(
      false
    );

    window.dispatchEvent(
      new CustomEvent(MUTATION_EVENT, { detail: { path: "/teachers/" } })
    );
    await Promise.resolve();

    expect(client.getQueryState(["catalog", "teachers", 0]).isInvalidated).toBe(
      true
    );
  });
});
