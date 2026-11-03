import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@academics/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});

import { CampusesPage } from "@academics/CampusesPage.jsx";
import {
  annexCampus,
  centralCampus,
  morningShift,
  paginated,
} from "./fixtures/academics.js";
import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";
import {
  academicsServiceMock,
  resetAcademicsServiceMock,
} from "./mocks/academicsService.js";

const DEFAULT_PARAMS = { page: 1, page_size: 25, ordering: "name" };

function renderWithRouter(ui, { permissions = ["scope.assign"], route } = {}) {
  return renderWithSession(ui, { user: sessionUser(permissions), route });
}

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
    expect(academicsServiceMock.listCampuses).toHaveBeenCalledWith(
      DEFAULT_PARAMS
    );
  });

  test("avisa cuando no hay sedes registradas", async () => {
    academicsServiceMock.listCampuses.mockResolvedValue(paginated([]));
    renderWithRouter(<CampusesPage />);

    expect(
      await screen.findByText("Todavía no hay sedes registradas.")
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
    await user.click(screen.getByLabelText(/^Mostrar desactivados/));

    await waitFor(() =>
      expect(academicsServiceMock.listCampuses).toHaveBeenLastCalledWith({
        ...DEFAULT_PARAMS,
        include_inactive: true,
      })
    );
    expect(await screen.findByText("Desactivada")).toBeInTheDocument();
  });

  test("crea una sede y recarga el listado", async () => {
    const user = userEvent.setup();
    renderWithRouter(<CampusesPage />);
    await screen.findByText("Sede Central");

    await user.click(screen.getByRole("button", { name: "Nueva sede" }));
    await user.type(
      screen.getByRole("textbox", { name: /^Nombre/ }),
      "Sede Norte"
    );
    await user.type(screen.getByLabelText(/^Código/), "norte");
    await user.type(screen.getByLabelText(/^Dirección/), "Zona 3");
    await user.click(screen.getByLabelText(/^Es la sede principal/));
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
    await user.type(
      screen.getByRole("textbox", { name: /^Nombre/ }),
      "Sede Norte"
    );
    await user.type(screen.getByLabelText(/^Código/), "CENTRAL");
    await user.click(screen.getByRole("button", { name: "Crear sede" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "El codigo ya existe en la institucion."
    );
    expect(screen.getByRole("textbox", { name: /^Nombre/ })).toHaveValue(
      "Sede Norte"
    );
  });

  test("edita sin ofrecer el codigo, que es inmutable", async () => {
    const user = userEvent.setup();
    renderWithRouter(<CampusesPage />);
    await screen.findByText("Sede Central");

    await user.click(screen.getByRole("button", { name: "Editar" }));

    expect(
      await screen.findByRole("heading", { name: "Editar Sede Central" })
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Código/)).not.toBeInTheDocument();

    await user.clear(screen.getByRole("textbox", { name: /^Nombre/ }));
    await user.type(
      screen.getByRole("textbox", { name: /^Nombre/ }),
      "Sede Principal"
    );
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
    expect(
      screen.getByText(/Se desactivará "Sede Central"/)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Sí, desactivar" }));

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
    // El dialogo marca el resto de la pagina con aria-hidden mientras esta
    // abierto, y lo quita al terminar la animacion de cierre: hay que esperar.
    expect(
      await screen.findByRole("button", { name: "Desactivar" })
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
    await user.click(screen.getByRole("button", { name: "Sí, desactivar" }));

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

    await user.click(screen.getByRole("button", { name: "Ver jornadas (2)" }));

    expect(
      await screen.findByRole("heading", { name: "Jornadas de Sede Central" })
    ).toBeInTheDocument();
    expect(academicsServiceMock.listCampusShifts).toHaveBeenCalledWith(
      "campus-central",
      DEFAULT_PARAMS
    );
    expect(screen.getByText("Matutina")).toBeInTheDocument();
  });

  test("crea una jornada dentro de la sede abierta", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCampusShifts.mockResolvedValue(paginated([]));
    renderWithRouter(<CampusesPage />);
    await screen.findByText("Sede Central");

    await user.click(screen.getByRole("button", { name: "Ver jornadas (2)" }));
    await user.click(
      await screen.findByRole("button", { name: "Nueva jornada" })
    );
    await user.type(
      screen.getByRole("textbox", { name: /^Nombre/ }),
      "Vespertina"
    );
    await user.type(screen.getByLabelText(/^Código/), "VES");
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

    expect(screen.getByText(/Mostrando 1–25 de 30/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Siguiente" }));

    await waitFor(() =>
      expect(academicsServiceMock.listCampuses).toHaveBeenLastCalledWith({
        ...DEFAULT_PARAMS,
        page: 2,
      })
    );
  });

  test("busca y ordena en el servidor", async () => {
    const user = userEvent.setup();
    renderWithRouter(<CampusesPage />);
    await screen.findByText("Sede Central");

    fireEvent.change(
      screen.getByPlaceholderText("Buscar sede por nombre o código"),
      { target: { value: "cen" } }
    );
    await waitFor(() =>
      expect(academicsServiceMock.listCampuses).toHaveBeenLastCalledWith({
        ...DEFAULT_PARAMS,
        search: "cen",
      })
    );

    await user.click(screen.getAllByLabelText("Ordenar por")[0]);
    await user.click(
      await screen.findByRole("option", { name: "Código (Z–A)" })
    );
    await waitFor(() =>
      expect(academicsServiceMock.listCampuses).toHaveBeenLastCalledWith({
        ...DEFAULT_PARAMS,
        search: "cen",
        ordering: "-code",
      })
    );
  });

  test("abre las jornadas al hacer clic en la fila de la sede", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCampusShifts.mockResolvedValue(
      paginated([morningShift])
    );
    renderWithRouter(<CampusesPage />);

    await user.click(await screen.findByText("Sede Central"));

    expect(await screen.findByText("Matutina")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Ocultar jornadas" })
    ).toBeInTheDocument();
  });

  test("sin scope.assign no ofrece crear, editar ni desactivar", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCampusShifts.mockResolvedValue(
      paginated([morningShift])
    );
    renderWithRouter(<CampusesPage />, { permissions: [] });
    await screen.findByText("Sede Central");

    expect(
      screen.queryByRole("button", { name: "Nueva sede" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Editar" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Desactivar" })
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Ver jornadas (2)" }));
    expect(await screen.findByText("Matutina")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Nueva jornada" })
    ).not.toBeInTheDocument();
  });
});
