import { useState } from "react";
import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { academicsService } from "@academics/academicsService.js";
import { EnrolmentAcademicFilters } from "@enrolments/EnrolmentAcademicFilters.jsx";
import { EMPTY_ACADEMIC_FILTERS } from "@enrolments/academicFilters.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import { selectOption } from "./helpers/selectOption.jsx";

vi.mock("@academics/academicsService.js", () => ({
  academicsService: { listSections: vi.fn() },
}));
vi.mock("@shared/catalogs/academicCatalogs.js", () => ({
  useCycleCatalog: () => ({
    options: [
      { value: "c1", label: "Ciclo 2026" },
      { value: "c2", label: "Ciclo 2027" },
    ],
  }),
  useGradeCatalog: () => ({
    options: [
      { value: "g1", label: "Primero" },
      { value: "g2", label: "Segundo" },
    ],
  }),
}));

const SECTION = {
  public_id: "s1",
  name: "A",
  grade: { name: "Primero" },
  shift: { name: "Matutina" },
};
const changed = vi.fn();

function Harness() {
  const [value, setValue] = useState(EMPTY_ACADEMIC_FILTERS);
  return (
    <EnrolmentAcademicFilters
      value={value}
      onChange={(next) => {
        setValue(next);
        changed(next);
      }}
    />
  );
}

describe("filtros académicos M5", () => {
  beforeEach(() => {
    changed.mockReset();
    academicsService.listSections
      .mockReset()
      .mockResolvedValue({ count: 1, results: [SECTION] });
  });

  it("no descarga secciones hasta elegir ciclo y acota por grado en el servidor", async () => {
    const user = userEvent.setup();
    renderWithRouter(<Harness />);
    expect(academicsService.listSections).not.toHaveBeenCalled();
    await selectOption(user, "Ciclo escolar", "Ciclo 2026");
    await waitFor(() =>
      expect(academicsService.listSections).toHaveBeenLastCalledWith(
        expect.objectContaining({
          academic_cycle_id: "c1",
          page: 1,
          grade_id: undefined,
        })
      )
    );
    await selectOption(user, "Grado", "Primero");
    await waitFor(() =>
      expect(academicsService.listSections).toHaveBeenLastCalledWith(
        expect.objectContaining({
          academic_cycle_id: "c1",
          grade_id: "g1",
          page: 1,
        })
      )
    );
    await selectOption(user, "Sección", "Primero · A · Matutina");
    expect(changed).toHaveBeenLastCalledWith({
      academic_cycle_id: "c1",
      grade_id: "g1",
      section: { value: "s1", label: "Primero · A · Matutina" },
    });
    await selectOption(user, "Grado", "Segundo");
    expect(changed).toHaveBeenLastCalledWith({
      academic_cycle_id: "c1",
      grade_id: "g2",
      section: null,
    });
    await selectOption(user, "Ciclo escolar", "Ciclo 2027");
    expect(changed).toHaveBeenLastCalledWith({
      academic_cycle_id: "c2",
      grade_id: "",
      section: null,
    });
  });

  it("recorre páginas a pedido y conserva la selección al explorar otras opciones", async () => {
    const rows = Array.from({ length: 25 }, (_, index) => ({
      ...SECTION,
      public_id: `s${index}`,
      name: `A${index}`,
    }));
    academicsService.listSections.mockImplementation(({ page }) =>
      Promise.resolve({
        count: 26,
        results:
          page === 1 ? rows : [{ ...SECTION, public_id: "s26", name: "B" }],
      })
    );
    const user = userEvent.setup();
    renderWithRouter(<Harness />);
    await selectOption(user, "Ciclo escolar", "Ciclo 2026");
    await screen.findByText("Página 1 de 2 · 26 secciones");
    expect(academicsService.listSections).toHaveBeenCalledTimes(1);
    await selectOption(user, "Sección", "Primero · A0 · Matutina");
    await user.click(
      screen.getByRole("button", { name: "Página siguiente de secciones" })
    );
    await screen.findByText("Página 2 de 2 · 26 secciones");
    expect(academicsService.listSections).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 2 })
    );
    expect(screen.getByRole("combobox", { name: "Sección" })).toHaveTextContent(
      "Primero · A0 · Matutina"
    );
    await selectOption(user, "Sección", "Primero · B · Matutina");
    expect(changed.mock.lastCall[0].section.value).toBe("s26");
    await selectOption(user, "Grado", "Segundo");
    await screen.findByText("Página 1 de 2 · 26 secciones");
    expect(academicsService.listSections).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 1, grade_id: "g2" })
    );
    expect(changed.mock.lastCall[0].section).toBeNull();
  });

  it("muestra error del servidor y permite reintentar sin borrar filtros", async () => {
    academicsService.listSections.mockRejectedValueOnce(
      new Error("No se pudieron consultar las secciones.")
    );
    const user = userEvent.setup();
    renderWithRouter(<Harness />);
    await selectOption(user, "Ciclo escolar", "Ciclo 2026");
    expect(
      await screen.findByText("No se pudieron consultar las secciones.")
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Reintentar secciones" })
    );
    await screen.findByText("Página 1 de 1 · 1 sección");
    expect(
      screen.getByRole("combobox", { name: "Ciclo escolar" })
    ).toHaveTextContent("Ciclo 2026");
    expect(academicsService.listSections).toHaveBeenCalledTimes(2);
  });

  it("ignora secciones que llegan tarde después de cambiar de ciclo", async () => {
    let resolveOld;
    academicsService.listSections.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve;
        })
    );
    const user = userEvent.setup();
    renderWithRouter(<Harness />);
    await selectOption(user, "Ciclo escolar", "Ciclo 2026");
    await selectOption(user, "Ciclo escolar", "Ciclo 2027");
    await screen.findByText("Página 1 de 1 · 1 sección");
    await act(async () => resolveOld({ count: 20, results: [] }));
    expect(screen.getByText("Página 1 de 1 · 1 sección")).toBeInTheDocument();
    expect(screen.queryByText(/20 secciones/)).not.toBeInTheDocument();
  });
});
