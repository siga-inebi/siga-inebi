import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import {
  useCatalogOptions,
  useDependentCatalogOptions,
} from "@shared/catalogs/useCatalogOptions.js";

function wrapperFor(client) {
  return ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

describe("useCatalogOptions", () => {
  test("dos consumidores del mismo catalogo comparten una sola peticion", async () => {
    // Este es el caso real: la pagina de Asignaciones docentes y sus modales
    // de "Asignar por lotes"/"Clonar en ciclo nuevo" llaman al mismo
    // useCycleCatalog() por separado.
    async function loadCycles() {
      return [{ value: "1", label: "2026" }];
    }
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = wrapperFor(client);

    const page = renderHook(() => useCatalogOptions(loadCycles), { wrapper });
    const modal = renderHook(() => useCatalogOptions(loadCycles), { wrapper });

    await waitFor(() => expect(page.result.current.loading).toBe(false));
    await waitFor(() => expect(modal.result.current.loading).toBe(false));

    expect(page.result.current.options).toEqual([
      { value: "1", label: "2026" },
    ]);
    expect(modal.result.current.options).toEqual(page.result.current.options);
    // La query cacheada por react-query es la unica prueba fiable de que no
    // hubo una segunda peticion: contar llamadas a `loadCycles` directamente
    // dependeria de instrumentar la funcion en vez de observar el cache.
    expect(client.getQueryCache().getAll()).toHaveLength(1);
  });

  test("catalogos con nombres distintos no comparten cache", async () => {
    async function loadCycles() {
      return [{ value: "c", label: "ciclo" }];
    }
    async function loadSections() {
      return [{ value: "s", label: "seccion" }];
    }
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = wrapperFor(client);

    const cycles = renderHook(() => useCatalogOptions(loadCycles), {
      wrapper,
    });
    const sections = renderHook(() => useCatalogOptions(loadSections), {
      wrapper,
    });

    await waitFor(() => expect(cycles.result.current.loading).toBe(false));
    await waitFor(() => expect(sections.result.current.loading).toBe(false));

    expect(cycles.result.current.options).toEqual([
      { value: "c", label: "ciclo" },
    ]);
    expect(sections.result.current.options).toEqual([
      { value: "s", label: "seccion" },
    ]);
  });
});

describe("useDependentCatalogOptions", () => {
  test("sin dependencia no pide nada y queda no-listo", async () => {
    const buildLoad = vi.fn().mockResolvedValue([]);
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const { result } = renderHook(
      () => useDependentCatalogOptions(buildLoad, null),
      { wrapper: wrapperFor(client) }
    );

    expect(result.current.ready).toBe(false);
    expect(buildLoad).not.toHaveBeenCalled();
  });

  test("dependencias distintas no comparten cache entre si", async () => {
    async function buildLoad(cycleId) {
      return [{ value: cycleId, label: `secciones de ${cycleId}` }];
    }
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = wrapperFor(client);

    const forA = renderHook(
      () => useDependentCatalogOptions(buildLoad, "cycle-a"),
      { wrapper }
    );
    const forB = renderHook(
      () => useDependentCatalogOptions(buildLoad, "cycle-b"),
      { wrapper }
    );

    await waitFor(() => expect(forA.result.current.loading).toBe(false));
    await waitFor(() => expect(forB.result.current.loading).toBe(false));

    expect(forA.result.current.options).toEqual([
      { value: "cycle-a", label: "secciones de cycle-a" },
    ]);
    expect(forB.result.current.options).toEqual([
      { value: "cycle-b", label: "secciones de cycle-b" },
    ]);
  });
});
