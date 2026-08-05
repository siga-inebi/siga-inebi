import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("../services/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});

import { CampusesPage } from "../pages/CampusesPage.jsx";
import {
  annexCampus,
  centralCampus,
  morningShift,
  paginated,
} from "./fixtures/academics.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import {
  academicsServiceMock,
  resetAcademicsServiceMock,
} from "./mocks/academicsService.js";

describe("pantalla de sedes", () => {
  beforeEach(() => {
    resetAcademicsServiceMock();
    academicsServiceMock.listCampuses.mockResolvedValue(
      paginated([centralCampus])
    );
  });

  test("lista las sedes con su codigo, jornadas y estado", async () => {
    renderWithRouter(<CampusesPage />);

    expect(await screen.findByText("Sede Central")).toBeInTheDocument();
    expect(screen.getByText("CENTRAL")).toBeInTheDocument();
    expect(screen.getByText("Activo")).toBeInTheDocument();
    expect(academicsServiceMock.listCampuses).toHaveBeenCalledWith({
      page: 1,
      include_inactive: false,
    });
  });

  test("avisa cuando no hay sedes registradas", async () => {
    academicsServiceMock.listCampuses.mockResolvedValue(paginated([]));
    renderWithRouter(<CampusesPage />);

    expect(
      await screen.findByText("Todavia no hay sedes registradas.")
    ).toBeInTheDocument();
  });

  test("muestra el error del listado sin romper la pantalla", async () => {
    academicsServiceMock.listCampuses.mockRejectedValue(
      new Error("No autenticado.")
    );
    renderWithRouter(<CampusesPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No autenticado."
    );
  });

  test("vuelve a consultar al pedir las desactivadas", async () => {
    const user = userEvent.setup();
    renderWithRouter(<CampusesPage />);
    await screen.findByText("Sede Central");

    academicsServiceMock.listCampuses.mockResolvedValue(
      paginated([centralCampus, annexCampus])
    );
    await user.click(screen.getByLabelText("Mostrar desactivadas"));

    await waitFor(() =>
      expect(academicsServiceMock.listCampuses).toHaveBeenLastCalledWith({
        page: 1,
        include_inactive: true,
      })
    );
    expect(await screen.findByText("Desactivado")).toBeInTheDocument();
  });

  test("crea una sede y recarga el listado", async () => {
    const user = userEvent.setup();
    renderWithRouter(<CampusesPage />);
    await screen.findByText("Sede Central");

    await user.click(screen.getByRole("button", { name: "Nueva sede" }));
    await user.type(screen.getByLabelText("Nombre"), "Sede Norte");
    await user.type(screen.getByLabelText("Codigo"), "norte");
    await user.type(screen.getByLabelText("Direccion"), "Zona 3");
    await user.click(screen.getByLabelText("Es la sede principal"));
    await user.click(screen.getByRole("button", { name: "Crear sede" }));

    await waitFor(() =>
      expect(academicsServiceMock.createCampus).toHaveBeenCalledWith({
        name: "Sede Norte",
        code: "norte",
        address: "Zona 3",
        is_main: true,
      })
    );
    await waitFor(() =>
      expect(academicsServiceMock.listCampuses).toHaveBeenCalledTimes(2)
    );
  });

  test("no envia el formulario si falta un campo obligatorio", async () => {
    const user = userEvent.setup();
    renderWithRouter(<CampusesPage />);
    await screen.findByText("Sede Central");

    await user.click(screen.getByRole("button", { name: "Nueva sede" }));
    await user.click(screen.getByRole("button", { name: "Crear sede" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Complete el campo nombre."
    );
    expect(academicsServiceMock.createCampus).not.toHaveBeenCalled();
  });

  test("conserva lo escrito cuando el backend rechaza el alta", async () => {
    const user = userEvent.setup();
    academicsServiceMock.createCampus.mockRejectedValue(
      new Error("El codigo ya existe en la institucion.")
    );
    renderWithRouter(<CampusesPage />);
    await screen.findByText("Sede Central");

    await user.click(screen.getByRole("button", { name: "Nueva sede" }));
    await user.type(screen.getByLabelText("Nombre"), "Sede Norte");
    await user.type(screen.getByLabelText("Codigo"), "CENTRAL");
    await user.click(screen.getByRole("button", { name: "Crear sede" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "El codigo ya existe en la institucion."
    );
    expect(screen.getByLabelText("Nombre")).toHaveValue("Sede Norte");
  });

  test("edita sin ofrecer el codigo, que es inmutable", async () => {
    const user = userEvent.setup();
    renderWithRouter(<CampusesPage />);
    await screen.findByText("Sede Central");

    await user.click(screen.getByRole("button", { name: "Editar" }));

    expect(
      await screen.findByRole("heading", { name: "Editar Sede Central" })
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Codigo")).not.toBeInTheDocument();

    await user.clear(screen.getByLabelText("Nombre"));
    await user.type(screen.getByLabelText("Nombre"), "Sede Principal");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() =>
      expect(academicsServiceMock.updateCampus).toHaveBeenCalledWith(
        "campus-central",
        {
          name: "Sede Principal",
          address: "Zona 1, Salcaja",
          is_main: true,
        }
      )
    );
  });

  test("desactiva solo despues de confirmar", async () => {
    const user = userEvent.setup();
    renderWithRouter(<CampusesPage />);
    await screen.findByText("Sede Central");

    await user.click(screen.getByRole("button", { name: "Desactivar" }));
    expect(academicsServiceMock.deactivateCampus).not.toHaveBeenCalled();
    expect(screen.getByText("Desactivar Sede Central?")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Si, desactivar" }));

    await waitFor(() =>
      expect(academicsServiceMock.deactivateCampus).toHaveBeenCalledWith(
        "campus-central"
      )
    );
  });

  test("cancelar la confirmacion no desactiva nada", async () => {
    const user = userEvent.setup();
    renderWithRouter(<CampusesPage />);
    await screen.findByText("Sede Central");

    await user.click(screen.getByRole("button", { name: "Desactivar" }));
    await user.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(academicsServiceMock.deactivateCampus).not.toHaveBeenCalled();
    expect(
      screen.getByRole("button", { name: "Desactivar" })
    ).toBeInTheDocument();
  });

  test("muestra el motivo cuando el backend rechaza la baja", async () => {
    const user = userEvent.setup();
    academicsServiceMock.deactivateCampus.mockRejectedValue(
      new Error("Un ciclo abierto usa jornadas de esta sede.")
    );
    renderWithRouter(<CampusesPage />);
    await screen.findByText("Sede Central");

    await user.click(screen.getByRole("button", { name: "Desactivar" }));
    await user.click(screen.getByRole("button", { name: "Si, desactivar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Un ciclo abierto usa jornadas de esta sede."
    );
  });

  test("no ofrece dar de baja una sede ya desactivada", async () => {
    academicsServiceMock.listCampuses.mockResolvedValue(
      paginated([annexCampus])
    );
    renderWithRouter(<CampusesPage />);

    expect(await screen.findByText("Sede Anexo")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Desactivar" })
    ).not.toBeInTheDocument();
  });

  test("abre las jornadas de la sede seleccionada", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCampusShifts.mockResolvedValue(
      paginated([morningShift])
    );
    renderWithRouter(<CampusesPage />);
    await screen.findByText("Sede Central");

    await user.click(screen.getByRole("button", { name: "Ver jornadas" }));

    expect(
      await screen.findByRole("heading", { name: "Jornadas de Sede Central" })
    ).toBeInTheDocument();
    expect(academicsServiceMock.listCampusShifts).toHaveBeenCalledWith(
      "campus-central",
      { page: 1, include_inactive: false }
    );
    expect(screen.getByText("Matutina")).toBeInTheDocument();
  });

  test("crea una jornada dentro de la sede abierta", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCampusShifts.mockResolvedValue(paginated([]));
    renderWithRouter(<CampusesPage />);
    await screen.findByText("Sede Central");

    await user.click(screen.getByRole("button", { name: "Ver jornadas" }));
    await user.click(
      await screen.findByRole("button", { name: "Nueva jornada" })
    );
    await user.type(screen.getByLabelText("Nombre"), "Vespertina");
    await user.type(screen.getByLabelText("Codigo"), "VES");
    await user.click(screen.getByRole("button", { name: "Crear jornada" }));

    await waitFor(() =>
      expect(academicsServiceMock.createShift).toHaveBeenCalledWith(
        "campus-central",
        { name: "Vespertina", code: "VES" }
      )
    );
  });

  test("pagina el listado cuando hay mas de una pagina", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCampuses.mockResolvedValue(
      paginated([centralCampus], {
        count: 30,
        next: "/academics/campuses/?page=2",
      })
    );
    renderWithRouter(<CampusesPage />);
    await screen.findByText("Sede Central");

    expect(screen.getByText(/Pagina 1 de 2/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Siguiente" }));

    await waitFor(() =>
      expect(academicsServiceMock.listCampuses).toHaveBeenLastCalledWith({
        page: 2,
        include_inactive: false,
      })
    );
  });
});
