import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@academics/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});

import { SubjectsPage } from "@academics/SubjectsPage.jsx";
import { artSubject, mathSubject, paginated } from "./fixtures/academics.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import {
  academicsServiceMock,
  resetAcademicsServiceMock,
} from "./mocks/academicsService.js";

describe("pantalla de cursos", () => {
  beforeEach(() => {
    resetAcademicsServiceMock();
    academicsServiceMock.listSubjects.mockResolvedValue(
      paginated([mathSubject])
    );
  });

  test("lista los cursos con los niveles en los que se imparten", async () => {
    renderWithRouter(<SubjectsPage />);

    expect(await screen.findByText("Matematica")).toBeInTheDocument();
    expect(screen.getByText("MAT")).toBeInTheDocument();
    expect(screen.getByText("Basico")).toBeInTheDocument();
  });

  test("marca como sin vincular los cursos que no estan en ningun nivel", async () => {
    academicsServiceMock.listSubjects.mockResolvedValue(
      paginated([artSubject])
    );
    renderWithRouter(<SubjectsPage />);

    expect(await screen.findByText("Sin vincular")).toBeInTheDocument();
  });

  test("crea un curso y recarga el listado", async () => {
    const user = userEvent.setup();
    renderWithRouter(<SubjectsPage />);
    await screen.findByText("Matematica");

    await user.click(screen.getByRole("button", { name: "Nuevo curso" }));
    await user.type(screen.getByLabelText(/^Nombre/), "  Comunicacion  ");
    await user.type(screen.getByLabelText(/^Codigo/), "COM");
    await user.click(screen.getByRole("button", { name: "Crear curso" }));

    await waitFor(() =>
      expect(academicsServiceMock.createSubject).toHaveBeenCalledWith({
        name: "Comunicacion",
        code: "COM",
      })
    );
    await waitFor(() =>
      expect(academicsServiceMock.listSubjects).toHaveBeenCalledTimes(2)
    );
  });

  test("edita solo el nombre, porque el codigo es inmutable", async () => {
    const user = userEvent.setup();
    renderWithRouter(<SubjectsPage />);
    await screen.findByText("Matematica");

    await user.click(screen.getByRole("button", { name: "Editar" }));
    expect(screen.queryByLabelText(/^Codigo/)).not.toBeInTheDocument();

    await user.clear(screen.getByLabelText(/^Nombre/));
    await user.type(screen.getByLabelText(/^Nombre/), "Matematicas");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() =>
      expect(academicsServiceMock.updateSubject).toHaveBeenCalledWith(
        "subject-mat",
        { name: "Matematicas" }
      )
    );
  });

  test("desactiva un curso tras confirmar", async () => {
    const user = userEvent.setup();
    renderWithRouter(<SubjectsPage />);
    await screen.findByText("Matematica");

    await user.click(screen.getByRole("button", { name: "Desactivar" }));
    await user.click(screen.getByRole("button", { name: "Si, desactivar" }));

    await waitFor(() =>
      expect(academicsServiceMock.deactivateSubject).toHaveBeenCalledWith(
        "subject-mat"
      )
    );
  });
});
