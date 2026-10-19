import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { describe, expect, test, vi } from "vitest";

import {
  SEARCH_DEBOUNCE_MS,
  useServerList,
} from "@shared/crud/useServerList.js";

function setup(route = "/lista", options = {}) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const fetchPage = vi.fn(async (params) => ({
    count: 120,
    next: null,
    previous: null,
    results: [{ id: `fila-${params.page ?? 1}` }],
  }));
  const location = { current: null };
  const wrapper = ({ children }) => (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
  const hook = renderHook(
    () => {
      location.current = useLocation();
      return useServerList({
        queryKey: ["prueba"],
        fetchPage,
        defaultFilters: { status: "" },
        ...options,
      });
    },
    { wrapper }
  );
  return { ...hook, fetchPage, location };
}

describe("useServerList (ux-ui 1.1)", () => {
  test("pide solo la pagina visible con el tamano por defecto", async () => {
    const { result, fetchPage } = setup();

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(fetchPage).toHaveBeenCalledWith({ page: 1, page_size: 25 });
    expect(result.current.count).toBe(120);
    expect(result.current.pageCount).toBe(5);
  });

  test("entrega siempre onRowsPerPageChange y guarda el tamano en la URL", async () => {
    const { result, fetchPage, location } = setup("/lista?page=3");
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.pagination.page).toBe(2);

    act(() => result.current.pagination.onRowsPerPageChange(50));

    await waitFor(() =>
      expect(fetchPage).toHaveBeenLastCalledWith({ page: 1, page_size: 50 })
    );
    // Cambiar el tamano vuelve a la pagina 1.
    expect(location.current.search).toBe("?page_size=50");
    expect(result.current.pagination.rowsPerPageOptions).toEqual([
      10, 25, 50, 100,
    ]);
  });

  test("lee pagina, tamano, busqueda y filtros desde la URL (recargar conserva la vista)", async () => {
    const { result, fetchPage } = setup(
      "/lista?page=2&page_size=10&search=ana&status=active&ordering=-last_login"
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(fetchPage).toHaveBeenCalledWith({
      page: 2,
      page_size: 10,
      search: "ana",
      status: "active",
      ordering: "-last_login",
    });
    expect(result.current.search).toBe("ana");
    expect(result.current.filters.status).toBe("active");
  });

  test("la busqueda espera antes de pedir y vuelve a la pagina 1", async () => {
    const { result, fetchPage, location } = setup("/lista?page=4");
    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => result.current.setSearch("lu"));
    act(() => result.current.setSearch("luis"));
    // Todavia no: se espera a que la persona deje de escribir.
    expect(location.current.search).toBe("?page=4");

    await waitFor(() => expect(location.current.search).toBe("?search=luis"), {
      timeout: SEARCH_DEBOUNCE_MS * 5,
    });
    await waitFor(() =>
      expect(fetchPage).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 25,
        search: "luis",
      })
    );
    // Una sola peticion de busqueda, no una por tecla.
    expect(
      fetchPage.mock.calls.filter(([params]) => params.search === "lu")
    ).toHaveLength(0);
  });

  test("un filtro se refleja en la URL y en los parametros de exportacion", async () => {
    const { result, location } = setup("/lista?page=2");
    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => result.current.setFilter("status", "disabled"));

    await waitFor(() =>
      expect(location.current.search).toBe("?status=disabled")
    );
    expect(result.current.exportParams).toEqual({ status: "disabled" });
  });

  test("dos listados conviven en la misma URL con prefijo", async () => {
    const { result, location } = setup("/lista", { urlPrefix: "roles_" });
    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => result.current.goToPage(3));

    await waitFor(() => expect(location.current.search).toBe("?roles_page=3"));
  });
});
