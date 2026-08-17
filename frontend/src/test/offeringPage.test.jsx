import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("../services/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});

vi.mock("../services/peopleService.js", async () => {
  const { peopleServiceMock } = await import("./mocks/peopleService.js");
  return { peopleService: peopleServiceMock };
});

import { OfferingPage } from "../pages/OfferingPage.jsx";
import {
  anaPerson,
  artPlanEntry,
  basicOffering,
  closedAssignment,
  inactivePerson,
  mathPlanEntry,
  openAssignment,
  paginated,
  sectionA,
  uncappedSection,
} from "./fixtures/academics.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import {
  academicsServiceMock,
  resetAcademicsServiceMock,
} from "./mocks/academicsService.js";
import {
  peopleServiceMock,
  resetPeopleServiceMock,
} from "./mocks/peopleService.js";

const ROUTE = `/app/ofertas/${basicOffering.public_id}`;

function renderOffering() {
  return renderWithRouter(
    <Routes>
      <Route element={<OfferingPage />} path="/app/ofertas/:offeringId" />
    </Routes>,
    { route: ROUTE }
  );
}

/** Abre el panel de docentes de la seccion A. */
async function openSection(user) {
  await screen.findByText("A");
  await user.click(screen.getByRole("button", { name: "Docentes" }));
  return screen.findByRole("heading", { name: "Docentes de la seccion A" });
}

describe("pantalla de oferta de grado", () => {
  beforeEach(() => {
    resetAcademicsServiceMock();
    resetPeopleServiceMock();
    academicsServiceMock.getOffering.mockResolvedValue(basicOffering);
    academicsServiceMock.listOfferingSections.mockResolvedValue(
      paginated([sectionA])
    );
  });

  test("muestra el grado, la jornada, la sede y el ciclo", async () => {
    renderOffering();

    expect(
      await screen.findByRole("heading", { name: /Primero Basico - Matutina/ })
    ).toBeInTheDocument();
    expect(screen.getByText(/Sede Central/)).toBeInTheDocument();
    expect(screen.getByText("Activo")).toBeInTheDocument();
    expect(academicsServiceMock.getOffering).toHaveBeenCalledWith(
      "offering-bas1-mat"
    );
  });

  test("informa cuando la oferta no existe", async () => {
    academicsServiceMock.getOffering.mockRejectedValue(
      new Error("Grade offering not found.")
    );
    renderOffering();

    expect(await screen.findByRole("alert")).toHaveTextContent("not found");
    expect(
      screen.getByRole("link", { name: "Volver a ciclos" })
    ).toBeInTheDocument();
  });

  test("lista las secciones con ocupacion y cupo disponible", async () => {
    renderOffering();

    expect(await screen.findByText("A")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("23")).toBeInTheDocument();
  });

  test("una seccion sin cupo declarado no reporta disponibles", async () => {
    academicsServiceMock.listOfferingSections.mockResolvedValue(
      paginated([uncappedSection])
    );
    renderOffering();

    expect(await screen.findByText("B")).toBeInTheDocument();
    expect(screen.getByText("Sin declarar")).toBeInTheDocument();
    expect(screen.getByText("Sin tope")).toBeInTheDocument();
  });

  test("crea una seccion", async () => {
    const user = userEvent.setup();
    renderOffering();
    await screen.findByText("A");

    await user.click(screen.getByRole("button", { name: "Nueva seccion" }));
    await user.type(screen.getByLabelText("Nombre"), "c");
    await user.clear(screen.getByLabelText("Cupo"));
    await user.type(screen.getByLabelText("Cupo"), "30");
    await user.click(screen.getByRole("button", { name: "Crear seccion" }));

    await waitFor(() =>
      expect(academicsServiceMock.createSection).toHaveBeenCalledWith(
        "offering-bas1-mat",
        { name: "c", capacity: 30 }
      )
    );
  });

  test("muestra el motivo cuando el cupo queda por debajo de la ocupacion", async () => {
    const user = userEvent.setup();
    academicsServiceMock.updateSection.mockRejectedValue(
      new Error("capacity cannot be set below that.")
    );
    renderOffering();
    await screen.findByText("A");

    await user.click(screen.getByRole("button", { name: "Editar" }));
    await user.clear(screen.getByLabelText("Cupo"));
    await user.type(screen.getByLabelText("Cupo"), "5");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "capacity cannot be set below"
    );
  });

  test("desactivar una seccion pide confirmacion", async () => {
    const user = userEvent.setup();
    renderOffering();
    await screen.findByText("A");

    await user.click(screen.getByRole("button", { name: "Desactivar" }));
    expect(academicsServiceMock.deactivateSection).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Si, desactivar" }));

    await waitFor(() =>
      expect(academicsServiceMock.deactivateSection).toHaveBeenCalledWith(
        "section-a"
      )
    );
  });

  test("al abrir una seccion carga sus docentes y el plan del grado", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listSectionAssignments.mockResolvedValue(
      paginated([openAssignment])
    );
    academicsServiceMock.listCurriculum.mockResolvedValue(
      paginated([mathPlanEntry])
    );
    renderOffering();

    await openSection(user);

    expect(academicsServiceMock.listSectionAssignments).toHaveBeenCalledWith(
      "section-a",
      { page: 1, include_inactive: false }
    );
    expect(academicsServiceMock.listCurriculum).toHaveBeenCalledWith(
      "cycle-2026",
      { page: 1, grade: "grade-bas1" }
    );
    expect(screen.getByText("Ana Lopez")).toBeInTheDocument();
    expect(screen.getByText("Vigente")).toBeInTheDocument();
  });

  test("avisa cuando el grado todavia no tiene plan de estudios", async () => {
    const user = userEvent.setup();
    renderOffering();
    await openSection(user);

    expect(
      await screen.findByText(/todavia no tiene plan de estudios/)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Asignar docente" })
    ).toBeDisabled();
  });

  test("solo ofrece cursos del plan que aun no tienen docente vigente", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCurriculum.mockResolvedValue(
      paginated([mathPlanEntry, artPlanEntry])
    );
    academicsServiceMock.listSectionAssignments.mockResolvedValue(
      paginated([openAssignment])
    );
    peopleServiceMock.listPeople.mockResolvedValue(
      paginated([anaPerson, inactivePerson])
    );
    renderOffering();
    await openSection(user);

    await user.click(
      await screen.findByRole("button", { name: "Asignar docente" })
    );

    const subject = screen.getByLabelText("Curso");
    expect(
      within(subject).getByRole("option", { name: "Artes Plasticas (ART)" })
    ).toBeInTheDocument();
    expect(
      within(subject).queryByRole("option", { name: /Matematica/ })
    ).not.toBeInTheDocument();
  });

  test("el selector de docentes deja fuera a las personas inactivas", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCurriculum.mockResolvedValue(
      paginated([mathPlanEntry])
    );
    peopleServiceMock.listPeople.mockResolvedValue(
      paginated([anaPerson, inactivePerson])
    );
    renderOffering();
    await openSection(user);

    await user.click(
      await screen.findByRole("button", { name: "Asignar docente" })
    );

    const teacher = screen.getByLabelText("Docente");
    expect(
      within(teacher).getByRole("option", { name: "Ana Lopez" })
    ).toBeInTheDocument();
    expect(
      within(teacher).queryByRole("option", { name: /Persona Inactiva/ })
    ).not.toBeInTheDocument();
  });

  test("asignar sin fecha deja que el backend use la de hoy", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCurriculum.mockResolvedValue(
      paginated([mathPlanEntry])
    );
    peopleServiceMock.listPeople.mockResolvedValue(paginated([anaPerson]));
    renderOffering();
    await openSection(user);

    await user.click(
      await screen.findByRole("button", { name: "Asignar docente" })
    );
    await user.selectOptions(screen.getByLabelText("Curso"), "subject-mat");
    await user.selectOptions(screen.getByLabelText("Docente"), "person-ana");
    await user.click(screen.getByRole("button", { name: "Asignar" }));

    await waitFor(() =>
      expect(academicsServiceMock.assignTeacher).toHaveBeenCalledWith(
        "section-a",
        { subject_id: "subject-mat", teacher_id: "person-ana" }
      )
    );
  });

  test("asignar con fecha explicita la envia", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCurriculum.mockResolvedValue(
      paginated([mathPlanEntry])
    );
    peopleServiceMock.listPeople.mockResolvedValue(paginated([anaPerson]));
    renderOffering();
    await openSection(user);

    await user.click(
      await screen.findByRole("button", { name: "Asignar docente" })
    );
    await user.selectOptions(screen.getByLabelText("Curso"), "subject-mat");
    await user.selectOptions(screen.getByLabelText("Docente"), "person-ana");
    await user.type(screen.getByLabelText("Desde"), "2026-03-01");
    await user.click(screen.getByRole("button", { name: "Asignar" }));

    await waitFor(() =>
      expect(academicsServiceMock.assignTeacher).toHaveBeenCalledWith(
        "section-a",
        {
          subject_id: "subject-mat",
          teacher_id: "person-ana",
          starts_on: "2026-03-01",
        }
      )
    );
  });

  test("cerrar una asignacion pide confirmacion", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listSectionAssignments.mockResolvedValue(
      paginated([openAssignment])
    );
    renderOffering();
    await openSection(user);

    await user.click(await screen.findByRole("button", { name: "Cerrar" }));
    expect(academicsServiceMock.endAssignment).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Si, cerrar" }));

    await waitFor(() =>
      expect(academicsServiceMock.endAssignment).toHaveBeenCalledWith(
        "assignment-mat"
      )
    );
  });

  test("las asignaciones cerradas solo aparecen al pedir el historial", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listSectionAssignments.mockResolvedValue(
      paginated([openAssignment])
    );
    renderOffering();
    await openSection(user);

    academicsServiceMock.listSectionAssignments.mockResolvedValue(
      paginated([openAssignment, closedAssignment])
    );
    await user.click(screen.getByLabelText("Ver historial"));

    await waitFor(() =>
      expect(
        academicsServiceMock.listSectionAssignments
      ).toHaveBeenLastCalledWith("section-a", {
        page: 1,
        include_inactive: true,
      })
    );
    expect(await screen.findByText("Luis Perez")).toBeInTheDocument();
  });

  test("una asignacion cerrada no ofrece volver a cerrarse", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listSectionAssignments.mockResolvedValue(
      paginated([closedAssignment])
    );
    renderOffering();
    await openSection(user);

    expect(await screen.findByText("Luis Perez")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Cerrar" })
    ).not.toBeInTheDocument();
  });

  test("un ciclo cerrado deja la oferta en solo lectura", async () => {
    academicsServiceMock.getOffering.mockResolvedValue({
      ...basicOffering,
      academic_cycle: { ...basicOffering.academic_cycle, status: "closed" },
    });
    renderOffering();

    expect(
      await screen.findByText(
        "El ciclo esta cerrado: las secciones ya no se pueden modificar."
      )
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Nueva seccion" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Editar" })
    ).not.toBeInTheDocument();
  });
});
