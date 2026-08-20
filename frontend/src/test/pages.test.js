import { describe, expect, test, vi } from "vitest";

import { collectAllPages } from "@shared/api/pages.js";

describe("collectAllPages", () => {
  test("sigue el enlace `next` hasta agotar el listado", async () => {
    const fetchPage = vi.fn(async ({ page }) =>
      page < 3
        ? { results: [`fila-${page}`], next: `?page=${page + 1}` }
        : { results: [`fila-${page}`], next: null }
    );

    await expect(collectAllPages(fetchPage)).resolves.toEqual([
      "fila-1",
      "fila-2",
      "fila-3",
    ]);
    expect(fetchPage).toHaveBeenCalledTimes(3);
  });

  test("se detiene en la primera pagina cuando no hay siguiente", async () => {
    const fetchPage = vi.fn(async () => ({ results: ["unica"], next: null }));

    await expect(collectAllPages(fetchPage)).resolves.toEqual(["unica"]);
    expect(fetchPage).toHaveBeenCalledTimes(1);
  });

  test("corta en el tope de paginas aunque el backend siga ofreciendo mas", async () => {
    // Un `next` que nunca termina no debe dejar la pantalla pidiendo paginas
    // para siempre: el tope existe para que un backend en mal estado degrade
    // la lista, no cuelgue el navegador.
    const fetchPage = vi.fn(async ({ page }) => ({
      results: [page],
      next: "?page=siguiente",
    }));

    const collected = await collectAllPages(fetchPage);

    expect(collected).toHaveLength(40);
    expect(fetchPage).toHaveBeenCalledTimes(40);
  });

  test("tolera una pagina sin resultados", async () => {
    const fetchPage = vi.fn(async () => ({}));

    await expect(collectAllPages(fetchPage)).resolves.toEqual([]);
  });
});
