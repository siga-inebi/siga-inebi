import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("../services/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});

import { CyclesPage } from "../pages/CyclesPage.jsx";
import {
  activeCycle,
  artSubject,
  basicLevel,
  basicOffering,
  centralCampus,
  closedCycle,
  draftCycle,
  firstGrade,
  mathPlanEntry,
  mathSubject,
  morningShift,
  paginated,
} from "./fixtures/academics.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import {
  academicsServiceMock,
  resetAcademicsServiceMock,
} from "./mocks/academicsService.js";

/** Deja lista la cadena nivel -> grado y sede -> jornada de los selectores. */
function withStructure() {
  academicsServiceMock.listLevels.mockResolvedValue(paginated([basicLevel]));
  academicsServiceMock.listLevelGrades.mockResolvedValue(
    paginated([firstGrade])
  );
  academicsServiceMock.listCampuses.mockResolvedValue(
    paginated([centralCampus])
  );
  academicsServiceMock.listCampusShifts.mockResolvedValue(
    paginated([morningShift])
  );
}

async function openCycle(user) {
  await screen.findByText("Ciclo 2026");
  await user.click(screen.getByRole("button", { name: "Abrir" }));
  return screen.findByRole("heading", {
    name: "Oferta de grados de Ciclo 2026",
  });
}

/**
 * El formulario abierto, por su titulo. Hace falta porque el filtro del plan y
 * los formularios comparten la etiqueta "Grado" en la misma pantalla.
 */
function formTitled(pattern) {
  return screen.getByRole("heading", { name: pattern }).closest("form");
}

describe("pantalla de ciclos", () => {
  beforeEach(() => {
    resetAcademicsServiceMock();
    academicsServiceMock.listCycles.mockResolvedValue(paginated([activeCycle]));
  });

  test("lista los ciclos con su estado y cuantos grados ofertan", async () => {
    renderWithRouter(<CyclesPage />);

    expect(await screen.findByText("Ciclo 2026")).toBeInTheDocument();
    expect(screen.getByText("Activo")).toBeInTheDocument();
    expect(screen.getByText("2026-01-15")).toBeInTheDocument();
  });

  test("distingue borrador, activo y cerrado", async () => {
    academicsServiceMock.listCycles.mockResolvedValue(
      paginated([draftCycle, activeCycle, closedCycle])
    );
    renderWithRouter(<CyclesPage />);

    expect(await screen.findByText("Borrador")).toBeInTheDocument();
    expect(screen.getByText("Activo")).toBeInTheDocument();
    expect(screen.getByText("Cerrado")).toBeInTheDocument();
  });

  test("crea un ciclo enviando las fechas", async () => {
    const user = userEvent.setup();
    renderWithRouter(<CyclesPage />);
    await screen.findByText("Ciclo 2026");

    await user.click(screen.getByRole("button", { name: "Nuevo ciclo" }));
    await user.type(screen.getByLabelText("Nombre"), "Ciclo 2027");
    await user.type(screen.getByLabelText("Inicio"), "2027-01-15");
    await user.type(screen.getByLabelText("Fin"), "2027-11-30");
    await user.click(screen.getByRole("button", { name: "Crear ciclo" }));

    await waitFor(() =>
      expect(academicsServiceMock.createCycle).toHaveBeenCalledWith({
        name: "Ciclo 2027",
        starts_on: "2027-01-15",
        ends_on: "2027-11-30",
      })
    );
  });

  test("activa un ciclo en borrador", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCycles.mockResolvedValue(paginated([draftCycle]));
    renderWithRouter(<CyclesPage />);
    await screen.findByText("Ciclo 2027");

    await user.click(screen.getByRole("button", { name: "Activar" }));

    await waitFor(() =>
      expect(academicsServiceMock.changeCycleStatus).toHaveBeenCalledWith(
        "cycle-2027",
        "active"
      )
    );
  });

  test("muestra el motivo cuando el ciclo no se puede activar", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCycles.mockResolvedValue(paginated([draftCycle]));
    academicsServiceMock.changeCycleStatus.mockRejectedValue(
      new Error("Cycle 'Ciclo 2027' has no grade offering yet.")
    );
    renderWithRouter(<CyclesPage />);
    await screen.findByText("Ciclo 2027");

    await user.click(screen.getByRole("button", { name: "Activar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "has no grade offering yet"
    );
  });

  test("cerrar un ciclo pide confirmacion porque no se reabre", async () => {
    const user = userEvent.setup();
    renderWithRouter(<CyclesPage />);
    await screen.findByText("Ciclo 2026");

    await user.click(screen.getByRole("button", { name: "Cerrar ciclo" }));
    expect(academicsServiceMock.changeCycleStatus).not.toHaveBeenCalled();
    expect(
      screen.getByText("Cerrar Ciclo 2026? No se puede reabrir.")
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Si, cerrar" }));

    await waitFor(() =>
      expect(academicsServiceMock.changeCycleStatus).toHaveBeenCalledWith(
        "cycle-2026",
        "closed"
      )
    );
  });

  test("un ciclo cerrado no ofrece editar ni cambiar de estado", async () => {
    academicsServiceMock.listCycles.mockResolvedValue(paginated([closedCycle]));
    renderWithRouter(<CyclesPage />);

    expect(await screen.findByText("Ciclo 2025")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Editar" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Cerrar ciclo|Activar/ })
    ).not.toBeInTheDocument();
  });

  test("al abrir un ciclo carga su oferta y su plan de estudios", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCycleOfferings.mockResolvedValue(
      paginated([basicOffering])
    );
    academicsServiceMock.listCurriculum.mockResolvedValue(
      paginated([mathPlanEntry])
    );
    renderWithRouter(<CyclesPage />);

    await openCycle(user);

    expect(academicsServiceMock.listCycleOfferings).toHaveBeenCalledWith(
      "cycle-2026",
      { page: 1, include_inactive: false }
    );
    expect(screen.getByText("Matutina")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Plan de estudios de Ciclo 2026" })
    ).toBeInTheDocument();
    expect(screen.getByText("Matematica")).toBeInTheDocument();
  });

  test("ofertar un grado usa los grados y jornadas de la institucion", async () => {
    const user = userEvent.setup();
    withStructure();
    renderWithRouter(<CyclesPage />);
    await openCycle(user);

    await user.click(
      await screen.findByRole("button", { name: "Ofertar grado" })
    );

    const form = formTitled(/Ofertar un grado/);
    await user.selectOptions(
      within(form).getByLabelText("Grado"),
      "grade-bas1"
    );
    await user.selectOptions(
      within(form).getByLabelText("Jornada"),
      "shift-mat"
    );
    await user.click(screen.getByRole("button", { name: "Ofertar" }));

    await waitFor(() =>
      expect(academicsServiceMock.createOffering).toHaveBeenCalledWith(
        "cycle-2026",
        { grade_id: "grade-bas1", shift_id: "shift-mat" }
      )
    );
  });

  test("la jornada del selector indica a que sede pertenece", async () => {
    const user = userEvent.setup();
    withStructure();
    renderWithRouter(<CyclesPage />);
    await openCycle(user);

    await user.click(
      await screen.findByRole("button", { name: "Ofertar grado" })
    );

    const select = screen.getByLabelText("Jornada");
    expect(
      within(select).getByRole("option", { name: "Matutina - Sede Central" })
    ).toBeInTheDocument();
  });

  test("agrega un curso al plan de un grado", async () => {
    const user = userEvent.setup();
    withStructure();
    academicsServiceMock.listSubjects.mockResolvedValue(
      paginated([mathSubject, artSubject])
    );
    renderWithRouter(<CyclesPage />);
    await openCycle(user);

    await user.click(
      await screen.findByRole("button", { name: "Agregar curso" })
    );

    const form = formTitled(/Agregar un curso al plan/);
    await user.selectOptions(
      within(form).getByLabelText("Grado"),
      "grade-bas1"
    );
    await user.selectOptions(
      within(form).getByLabelText("Curso"),
      "subject-art"
    );
    await user.click(screen.getByRole("button", { name: "Agregar al plan" }));

    await waitFor(() =>
      expect(academicsServiceMock.addCurriculumEntry).toHaveBeenCalledWith(
        "cycle-2026",
        { grade_id: "grade-bas1", subject_id: "subject-art", is_required: true }
      )
    );
  });

  test("filtrar el plan por grado vuelve a consultar", async () => {
    const user = userEvent.setup();
    withStructure();
    renderWithRouter(<CyclesPage />);
    await openCycle(user);

    await user.selectOptions(
      await screen.findByLabelText("Grado"),
      "grade-bas1"
    );

    await waitFor(() =>
      expect(academicsServiceMock.listCurriculum).toHaveBeenLastCalledWith(
        "cycle-2026",
        { page: 1, include_inactive: false, grade: "grade-bas1" }
      )
    );
  });

  test("quitar un curso del plan pide confirmacion", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCurriculum.mockResolvedValue(
      paginated([mathPlanEntry])
    );
    renderWithRouter(<CyclesPage />);
    await openCycle(user);

    await user.click(await screen.findByRole("button", { name: "Quitar" }));
    expect(academicsServiceMock.removeCurriculumEntry).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Si, quitar" }));

    await waitFor(() =>
      expect(academicsServiceMock.removeCurriculumEntry).toHaveBeenCalledWith(
        "plan-bas1-mat"
      )
    );
  });

  test("muestra el motivo cuando el curso no se puede quitar", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCurriculum.mockResolvedValue(
      paginated([mathPlanEntry])
    );
    academicsServiceMock.removeCurriculumEntry.mockRejectedValue(
      new Error("Subject still has an open teaching assignment.")
    );
    renderWithRouter(<CyclesPage />);
    await openCycle(user);

    await user.click(await screen.findByRole("button", { name: "Quitar" }));
    await user.click(screen.getByRole("button", { name: "Si, quitar" }));

    expect(
      await screen.findByText(/open teaching assignment/)
    ).toBeInTheDocument();
  });

  test("un ciclo cerrado muestra su estructura en solo lectura", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCycles.mockResolvedValue(paginated([closedCycle]));
    academicsServiceMock.listCycleOfferings.mockResolvedValue(
      paginated([basicOffering])
    );
    academicsServiceMock.listCurriculum.mockResolvedValue(
      paginated([mathPlanEntry])
    );
    renderWithRouter(<CyclesPage />);

    await screen.findByText("Ciclo 2025");
    await user.click(screen.getByRole("button", { name: "Abrir" }));

    expect(
      await screen.findByText(
        "El ciclo esta cerrado: su estructura ya no se puede modificar."
      )
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Ofertar grado" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Agregar curso" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Quitar" })
    ).not.toBeInTheDocument();
  });
});
