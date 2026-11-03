import { describe, expect, test, vi } from "vitest";

import {
  COLLECT_PAGE_SIZE,
  IncompleteListError,
  collectAllPages,
} from "@shared/api/pages.js";

describe("collectAllPages", () => {
  test("sigue el enlace `next` hasta agotar el listado", async () => {
    const fetchPage = vi.fn(async ({ page }) =>
      page < 3
        ? { results: [`fila-${page}`], next: `?page=${page + 1}`, count: 3 }
        : { results: [`fila-${page}`], next: null, count: 3 }
    );

    await expect(collectAllPages(fetchPage)).resolves.toEqual([
      "fila-1",
      "fila-2",
      "fila-3",
    ]);
    expect(fetchPage).toHaveBeenCalledTimes(3);
  });

  test("pide paginas del tamano maximo del backend", async () => {
    const fetchPage = vi.fn(async () => ({ results: ["unica"], next: null }));

    await collectAllPages(fetchPage);

    expect(fetchPage).toHaveBeenCalledWith({
      page: 1,
      page_size: COLLECT_PAGE_SIZE,
    });
  });

  test("no trunca: recorre mas de 1 000 registros (antes cortaba en 40 paginas)", async () => {
    // ux-ui 1.1.3: el tope de 40 x 25 = 1 000 filas hacia desaparecer el resto
    // sin aviso. 45 paginas de 25 deben llegar completas.
    const total = 45 * 25;
    const fetchPage = vi.fn(async ({ page }) => ({
      results: Array.from(
        { length: 25 },
        (_, index) => (page - 1) * 25 + index
      ),
      next: page < 45 ? `?page=${page + 1}` : null,
      count: total,
    }));

    const collected = await collectAllPages(fetchPage, { pageSize: 25 });

    expect(collected).toHaveLength(total);
    expect(fetchPage).toHaveBeenCalledTimes(45);
  });

  test("informa el avance de cada pagina", async () => {
    const onProgress = vi.fn();
    const fetchPage = vi.fn(async ({ page }) => ({
      results: [page],
      next: page < 2 ? "?page=2" : null,
      count: 2,
    }));

    await collectAllPages(fetchPage, { onProgress });

    expect(onProgress).toHaveBeenNthCalledWith(1, { loaded: 1, total: 2 });
    expect(onProgress).toHaveBeenNthCalledWith(2, { loaded: 2, total: 2 });
  });

  test("un backend que no termina falla de forma explicita, no silenciosa", async () => {
    const fetchPage = vi.fn(async ({ page }) => ({
      results: [page],
      next: "?page=siguiente",
      count: 3,
    }));

    await expect(collectAllPages(fetchPage)).rejects.toBeInstanceOf(
      IncompleteListError
    );
    expect(fetchPage.mock.calls.length).toBeLessThanOrEqual(4);
  });

  test("una pagina vacia que anuncia mas resultados es un error", async () => {
    const fetchPage = vi.fn(async () => ({ results: [], next: "?page=2" }));

    await expect(collectAllPages(fetchPage)).rejects.toThrow(/incompleto/);
  });

  test("se puede cancelar entre paginas", async () => {
    const controller = new AbortController();
    const fetchPage = vi.fn(async ({ page }) => {
      controller.abort();
      return { results: [page], next: "?page=2", count: 10 };
    });

    await expect(
      collectAllPages(fetchPage, { signal: controller.signal })
    ).rejects.toThrow(/cancelada/);
    expect(fetchPage).toHaveBeenCalledTimes(1);
  });

  test("tolera una pagina sin resultados", async () => {
    const fetchPage = vi.fn(async () => ({}));

    await expect(collectAllPages(fetchPage)).resolves.toEqual([]);
  });
});
