import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@cycles/cyclesService.js", async (importOriginal) => {
  const original = await importOriginal();
  return {
    ...original,
    cyclesService: {
      list: vi.fn(),
      close: vi.fn(),
      activate: vi.fn(),
      create: vi.fn(),
      clone: vi.fn(),
      get: vi.fn(),
      defaults: vi.fn(),
    },
  };
});

import { CyclesPage } from "@cycles/CyclesPage.jsx";
import { cyclesService } from "@cycles/cyclesService.js";
import { paginated } from "./fixtures/academics.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const cycle = (overrides) => ({
  public_id: "c1",
  year: 2026,
  name: "Ciclo 2026",
  starts_on: "2026-01-15",
  ends_on: "2026-10-31",
  description: "",
  status: "active",
  ...overrides,
});

describe("pantalla de ciclos: cerrar ciclo", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  test("ofrece cerrar solo el ciclo activo", async () => {
    cyclesService.list.mockResolvedValue(
      paginated([
        cycle({ public_id: "a", name: "Ciclo vigente", status: "active" }),
        cycle({
          public_id: "b",
          name: "Ciclo planeado",
          year: 2027,
          status: "draft",
        }),
        cycle({
          public_id: "c",
          name: "Ciclo historico",
          year: 2025,
          status: "closed",
        }),
      ])
    );
    renderWithRouter(<CyclesPage />);

    await screen.findByText("Ciclo vigente");
    expect(
      screen.getAllByRole("button", { name: "Cerrar ciclo" })
    ).toHaveLength(1);
  });

  test("cierra el ciclo tras confirmar y recarga el listado", async () => {
    const user = userEvent.setup();
    cyclesService.list.mockResolvedValue(paginated([cycle()]));
    cyclesService.close.mockResolvedValue(cycle({ status: "closed" }));
    renderWithRouter(<CyclesPage />);

    await user.click(
      await screen.findByRole("button", { name: "Cerrar ciclo" })
    );
    await user.click(screen.getByRole("button", { name: "Si, cerrar ciclo" }));

    await waitFor(() => expect(cyclesService.close).toHaveBeenCalledWith("c1"));
    await waitFor(() => expect(cyclesService.list).toHaveBeenCalledTimes(2));
  });

  test("muestra el motivo del backend si el cierre se rechaza", async () => {
    const user = userEvent.setup();
    cyclesService.list.mockResolvedValue(paginated([cycle()]));
    cyclesService.close.mockRejectedValue(
      new Error("la unidad de evaluacion 'U1' sigue abierta")
    );
    renderWithRouter(<CyclesPage />);

    await user.click(
      await screen.findByRole("button", { name: "Cerrar ciclo" })
    );
    await user.click(screen.getByRole("button", { name: "Si, cerrar ciclo" }));

    expect(await screen.findAllByText(/sigue abierta/)).not.toHaveLength(0);
  });
});
