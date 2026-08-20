import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@academics/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});

import { LevelsPage } from "@academics/LevelsPage.jsx";
import {
  artSubject,
  basicLevel,
  firstGrade,
  mathLink,
  mathSubject,
  paginated,
} from "./fixtures/academics.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import {
  academicsServiceMock,
  resetAcademicsServiceMock,
} from "./mocks/academicsService.js";

/** Abre el detalle del nivel y espera a que carguen sus dos paneles. */
async function openLevel(user) {
  await screen.findByText("Basico");
  await user.click(screen.getByRole("button", { name: "Abrir detalle" }));
  return screen.findByRole("heading", { name: "Grados del nivel" });
}

describe("pantalla de niveles", () => {
  beforeEach(() => {
    resetAcademicsServiceMock();
    academicsServiceMock.listLevels.mockResolvedValue(paginated([basicLevel]));
  });

  test("lista los niveles con su orden y sus conteos", async () => {
    renderWithRouter(<LevelsPage />);

    expect(await screen.findByText("Basico")).toBeInTheDocument();
    expect(screen.getByText("BAS")).toBeInTheDocument();
    expect(academicsServiceMock.listLevels).toHaveBeenCalledWith({
      page: 1,
      include_inactive: false,
    });
  });

  test("crea un nivel con el codigo que sugiere el backend", async () => {
    const user = userEvent.setup();
    academicsServiceMock.nextLevelCode.mockResolvedValue("NIV-02");
    renderWithRouter(<LevelsPage />);
    await screen.findByText("Basico");

    await user.click(screen.getByRole("button", { name: "Nuevo nivel" }));
    // El codigo llega puesto: se pide al abrir, no mientras el formulario esta
    // abierto, para que no cambie debajo de quien escribe.
    expect(await screen.findByDisplayValue("NIV-02")).toBeInTheDocument();
    await user.type(screen.getByLabelText(/^Nombre/), "Diversificado");
    await user.click(screen.getByRole("button", { name: "Crear nivel" }));

    await waitFor(() =>
      expect(academicsServiceMock.createLevel).toHaveBeenCalledWith({
        name: "Diversificado",
        code: "NIV-02",
      })
    );
  });

  test("el nivel se ubica por posicion, no por numero de secuencia", async () => {
    const user = userEvent.setup();
    renderWithRouter(<LevelsPage />);
    await screen.findByText("Basico");

    await user.click(screen.getByRole("button", { name: "Nuevo nivel" }));
    await user.type(screen.getByLabelText(/^Nombre/), "Diversificado");
    await user.click(screen.getByRole("combobox", { name: /Posicion/ }));
    await user.click(
      await screen.findByRole("option", { name: "Despues de Basico" })
    );
    await user.click(screen.getByRole("button", { name: "Crear nivel" }));

    await waitFor(() =>
      expect(academicsServiceMock.createLevel).toHaveBeenCalledWith(
        expect.objectContaining({ insert_after: "level-basico" })
      )
    );
  });

  test('"al inicio" viaja como null, y "al final" no viaja', async () => {
    const user = userEvent.setup();
    renderWithRouter(<LevelsPage />);
    await screen.findByText("Basico");

    // Al final es el valor por omision: la clave NO se manda, porque ausente es
    // lo que el backend lee como "al final". Mandar null lo pondria primero.
    await user.click(screen.getByRole("button", { name: "Nuevo nivel" }));
    await user.type(screen.getByLabelText(/^Nombre/), "Diversificado");
    await user.click(screen.getByRole("button", { name: "Crear nivel" }));

    await waitFor(() =>
      expect(academicsServiceMock.createLevel).toHaveBeenCalledWith({
        name: "Diversificado",
        code: "",
      })
    );

    await user.click(screen.getByRole("button", { name: "Nuevo nivel" }));
    await user.type(screen.getByLabelText(/^Nombre/), "Preprimaria");
    await user.click(screen.getByRole("combobox", { name: /Posicion/ }));
    await user.click(await screen.findByRole("option", { name: "Al inicio" }));
    await user.click(screen.getByRole("button", { name: "Crear nivel" }));

    await waitFor(() =>
      expect(academicsServiceMock.createLevel).toHaveBeenCalledWith(
        expect.objectContaining({ insert_after: null })
      )
    );
  });

  test("al abrir un nivel carga sus grados y su plan de estudios", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listLevelGrades.mockResolvedValue(
      paginated([firstGrade])
    );
    academicsServiceMock.listLevelSubjects.mockResolvedValue(
      paginated([mathLink])
    );
    renderWithRouter(<LevelsPage />);

    await openLevel(user);

    expect(academicsServiceMock.listLevelGrades).toHaveBeenCalledWith(
      "level-basico",
      { page: 1, include_inactive: false }
    );
    expect(academicsServiceMock.listLevelSubjects).toHaveBeenCalledWith(
      "level-basico",
      { page: 1, include_inactive: false }
    );
    expect(screen.getByText("Primero Basico")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Plan de estudios" })
    ).toBeInTheDocument();
    expect(screen.getByText("Matematica")).toBeInTheDocument();
  });

  test("crea un grado con el codigo derivado de su nivel", async () => {
    const user = userEvent.setup();
    academicsServiceMock.nextGradeCode.mockResolvedValue("BAS2");
    renderWithRouter(<LevelsPage />);
    await openLevel(user);

    await user.click(screen.getByRole("button", { name: "Nuevo grado" }));
    expect(await screen.findByDisplayValue("BAS2")).toBeInTheDocument();
    await user.type(screen.getByLabelText(/^Nombre/), "Segundo Basico");
    await user.click(screen.getByRole("button", { name: "Crear grado" }));

    await waitFor(() =>
      expect(academicsServiceMock.createGrade).toHaveBeenCalledWith(
        "level-basico",
        { name: "Segundo Basico", code: "BAS2" }
      )
    );
    expect(academicsServiceMock.nextGradeCode).toHaveBeenCalledWith(
      "level-basico"
    );
  });

  test("solo ofrece vincular cursos que aun no estan en el plan", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listLevelSubjects.mockResolvedValue(
      paginated([mathLink])
    );
    academicsServiceMock.listSubjects.mockResolvedValue(
      paginated([mathSubject, artSubject])
    );
    renderWithRouter(<LevelsPage />);
    await openLevel(user);

    await user.click(
      await screen.findByRole("button", { name: "Vincular curso" })
    );

    // El Select de MUI monta sus opciones en un portal solo al abrirse, asi que
    // hay que abrirlo para poder inspeccionar que ofrece.
    await user.click(screen.getByLabelText(/^Curso/));
    const listbox = await screen.findByRole("listbox");
    expect(
      within(listbox).getByRole("option", { name: "Artes Plasticas (ART)" })
    ).toBeInTheDocument();
    expect(
      within(listbox).queryByRole("option", { name: /Matematica/ })
    ).not.toBeInTheDocument();

    await user.click(
      within(listbox).getByRole("option", { name: "Artes Plasticas (ART)" })
    );
    await user.click(screen.getByRole("button", { name: "Vincular" }));

    await waitFor(() =>
      expect(academicsServiceMock.linkSubjectToLevel).toHaveBeenCalledWith(
        "level-basico",
        { subject_id: "subject-art", is_required: true, weekly_hours: 0 }
      )
    );
  });

  test("avisa cuando ya no queda ningun curso por vincular", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listLevelSubjects.mockResolvedValue(
      paginated([mathLink])
    );
    academicsServiceMock.listSubjects.mockResolvedValue(
      paginated([mathSubject])
    );
    renderWithRouter(<LevelsPage />);
    await openLevel(user);

    expect(
      await screen.findByText(
        "Todos los cursos activos ya estan vinculados a este nivel."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Vincular curso" })
    ).toBeDisabled();
  });

  test("desvincula un curso del plan tras confirmar", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listLevelSubjects.mockResolvedValue(
      paginated([mathLink])
    );
    renderWithRouter(<LevelsPage />);
    await openLevel(user);

    await user.click(
      await screen.findByRole("button", { name: "Desvincular" })
    );
    expect(academicsServiceMock.unlinkSubjectFromLevel).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Si, desvincular" }));

    await waitFor(() =>
      expect(academicsServiceMock.unlinkSubjectFromLevel).toHaveBeenCalledWith(
        "level-basico",
        "subject-mat"
      )
    );
  });

  test("actualiza la carga horaria del vinculo", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listLevelSubjects.mockResolvedValue(
      paginated([mathLink])
    );
    renderWithRouter(<LevelsPage />);
    await openLevel(user);

    // Cada seccion es una region con nombre, asi que se puede acotar la busqueda
    // al plan de estudios sin depender de clases CSS.
    const planSection = screen.getByRole("region", {
      name: "Plan de estudios",
    });
    await user.click(
      within(planSection).getByRole("button", { name: "Editar" })
    );

    await user.clear(screen.getByLabelText(/^Horas semanales/));
    await user.type(screen.getByLabelText(/^Horas semanales/), "6");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() =>
      expect(academicsServiceMock.updateLevelSubject).toHaveBeenCalledWith(
        "level-basico",
        "subject-mat",
        { is_required: true, weekly_hours: 6 }
      )
    );
  });

  test("muestra el motivo cuando el backend rechaza la baja del nivel", async () => {
    const user = userEvent.setup();
    academicsServiceMock.deactivateLevel.mockRejectedValue(
      new Error("Un ciclo abierto oferta grados de este nivel.")
    );
    renderWithRouter(<LevelsPage />);
    await screen.findByText("Basico");

    await user.click(screen.getByRole("button", { name: "Desactivar" }));
    await user.click(screen.getByRole("button", { name: "Si, desactivar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Un ciclo abierto oferta grados de este nivel."
    );
  });
});
