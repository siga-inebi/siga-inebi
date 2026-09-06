import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

const studentsServiceMock = vi.hoisted(() => ({ listPage: vi.fn() }));
const teachersServiceMock = vi.hoisted(() => ({ listPage: vi.fn() }));
const guardiansServiceMock = vi.hoisted(() => ({ listPage: vi.fn() }));

vi.mock("@students/studentsService.js", () => ({
  studentsService: studentsServiceMock,
}));
vi.mock("@teachers/teachersService.js", () => ({
  teachersService: teachersServiceMock,
}));
vi.mock("@guardians/guardiansService.js", () => ({
  guardiansService: guardiansServiceMock,
}));

import { useModuleCounts } from "@app/useModuleCounts.js";

function wrapperFor(client) {
  return ({ children }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
}

describe("useModuleCounts", () => {
  beforeEach(() => {
    studentsServiceMock.listPage.mockReset().mockResolvedValue({ count: 100 });
    teachersServiceMock.listPage.mockReset().mockResolvedValue({ count: 12 });
    guardiansServiceMock.listPage.mockReset().mockResolvedValue({ count: 34 });
  });

  test("expone el conteo de cada modulo", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const { result } = renderHook(() => useModuleCounts(true), {
      wrapper: wrapperFor(client),
    });

    await waitFor(() =>
      expect(result.current).toEqual({ alumnos: 100, docentes: 12, padres: 34 })
    );
  });

  test("deshabilitado no pide nada y devuelve null", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    renderHook(() => useModuleCounts(false), { wrapper: wrapperFor(client) });

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(studentsServiceMock.listPage).not.toHaveBeenCalled();
    expect(teachersServiceMock.listPage).not.toHaveBeenCalled();
    expect(guardiansServiceMock.listPage).not.toHaveBeenCalled();
  });

  test("remontar el hook (una navegacion) no vuelve a pedir los 3 catalogos", async () => {
    // Esto es lo que reemplaza el ×2/×4/×6 por navegacion del audit:
    // PrivateLayout se desmonta y remonta en cada cambio de ruta, y antes eso
    // volvia a pedir /students/, /teachers/ y /students/guardians/ cada vez.
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 5 * 60_000 } },
    });
    const wrapper = wrapperFor(client);

    const first = renderHook(() => useModuleCounts(true), { wrapper });
    await waitFor(() =>
      expect(first.result.current).toEqual({
        alumnos: 100,
        docentes: 12,
        padres: 34,
      })
    );
    first.unmount();

    const second = renderHook(() => useModuleCounts(true), { wrapper });
    await waitFor(() =>
      expect(second.result.current).toEqual({
        alumnos: 100,
        docentes: 12,
        padres: 34,
      })
    );

    expect(studentsServiceMock.listPage).toHaveBeenCalledTimes(1);
    expect(teachersServiceMock.listPage).toHaveBeenCalledTimes(1);
    expect(guardiansServiceMock.listPage).toHaveBeenCalledTimes(1);
  });
});
