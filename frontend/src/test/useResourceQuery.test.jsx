import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";

import { useResourceQuery } from "@shared/api/useResourceQuery.js";

function withClient() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return {
    client,
    wrapper: ({ children }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    ),
  };
}

describe("useResourceQuery", () => {
  test("dos instancias con la misma key comparten una sola peticion", async () => {
    // Esto es lo que reemplaza el ×2/×4/×8 del audit: dos componentes que piden
    // lo mismo no deberian generar dos peticiones de red.
    const fetcher = vi.fn().mockResolvedValue({ value: 1 });
    const { wrapper } = withClient();

    const first = renderHook(() => useResourceQuery(["shared"], fetcher), {
      wrapper,
    });
    const second = renderHook(() => useResourceQuery(["shared"], fetcher), {
      wrapper,
    });

    await waitFor(() => expect(first.result.current.loading).toBe(false));
    await waitFor(() => expect(second.result.current.loading).toBe(false));

    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(first.result.current.data).toEqual({ value: 1 });
    expect(second.result.current.data).toEqual({ value: 1 });
  });

  test("keys distintas piden por separado", async () => {
    const fetcher = vi.fn().mockResolvedValue({ value: 1 });
    const { wrapper } = withClient();

    renderHook(() => useResourceQuery(["a"], fetcher), { wrapper });
    renderHook(() => useResourceQuery(["b"], fetcher), { wrapper });

    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  });

  test("expone el error del fetcher como texto", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("Sin permiso."));
    const { wrapper } = withClient();

    const { result } = renderHook(() => useResourceQuery(["err"], fetcher), {
      wrapper,
    });

    await waitFor(() => expect(result.current.error).toBe("Sin permiso."));
  });

  test("enabled=false no dispara la peticion", async () => {
    const fetcher = vi.fn().mockResolvedValue({ value: 1 });
    const { wrapper } = withClient();

    renderHook(() => useResourceQuery(["off"], fetcher, { enabled: false }), {
      wrapper,
    });

    await act(async () => {});
    expect(fetcher).not.toHaveBeenCalled();
  });
});
