import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { useSearchableCatalog } from "@shared/catalogs/useSearchableCatalog.js";

function wrapperFor(client) {
  return ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

const mapResult = (row) => ({ value: row.id, label: row.name });

describe("useSearchableCatalog", () => {
  test("bajo el largo minimo no pide nada y queda no-listo", () => {
    const fetchPage = vi.fn();
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const { result } = renderHook(
      () => useSearchableCatalog("things", fetchPage, mapResult, "a"),
      { wrapper: wrapperFor(client) }
    );

    expect(result.current.ready).toBe(false);
    expect(result.current.options).toEqual([]);
    expect(fetchPage).not.toHaveBeenCalled();
  });

  test("con el largo minimo pide al backend y mapea los resultados", async () => {
    const fetchPage = vi
      .fn()
      .mockResolvedValue({ results: [{ id: "1", name: "Ana" }] });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const { result } = renderHook(
      () => useSearchableCatalog("things", fetchPage, mapResult, "an"),
      { wrapper: wrapperFor(client) }
    );

    await waitFor(() =>
      expect(result.current.options).toEqual([{ value: "1", label: "Ana" }])
    );
    expect(fetchPage).toHaveBeenCalledWith({ search: "an" });
  });

  test("terminos distintos no comparten cache", async () => {
    const fetchPage = vi
      .fn()
      .mockResolvedValueOnce({ results: [{ id: "1", name: "Ana" }] })
      .mockResolvedValueOnce({ results: [{ id: "2", name: "Luis" }] });
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = wrapperFor(client);

    const forAna = renderHook(
      () => useSearchableCatalog("things", fetchPage, mapResult, "ana"),
      { wrapper }
    );
    const forLuis = renderHook(
      () => useSearchableCatalog("things", fetchPage, mapResult, "luis"),
      { wrapper }
    );

    await waitFor(() =>
      expect(forAna.result.current.options).toEqual([
        { value: "1", label: "Ana" },
      ])
    );
    await waitFor(() =>
      expect(forLuis.result.current.options).toEqual([
        { value: "2", label: "Luis" },
      ])
    );
    expect(fetchPage).toHaveBeenCalledTimes(2);
  });
});
