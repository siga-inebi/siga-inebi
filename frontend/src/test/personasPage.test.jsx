import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("../services/peopleService.js", async () => {
  const { peopleServiceMock } = await import("./mocks/peopleService.js");
  return { peopleService: peopleServiceMock };
});

import { PersonasPage } from "../pages/PersonasPage.jsx";
import { paginated } from "./fixtures/academics.js";
import { anaPerson, carlosPerson } from "./fixtures/people.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import {
  peopleServiceMock,
  resetPeopleServiceMock,
} from "./mocks/peopleService.js";

describe("pantalla de personas", () => {
  beforeEach(() => {
    resetPeopleServiceMock();
    peopleServiceMock.listPeople.mockResolvedValue(paginated([anaPerson]));
  });

  test("lista las personas registradas", async () => {
    renderWithRouter(<PersonasPage />);

    expect(await screen.findByText("Ana Gomez")).toBeInTheDocument();
    expect(screen.getByText("ana.gomez@example.test")).toBeInTheDocument();
    expect(screen.getByText("50212345678")).toBeInTheDocument();
    expect(screen.getByText("INEBI-001")).toBeInTheDocument();
  });

  test("muestra 'sin registrar' para los campos opcionales vacios", async () => {
    peopleServiceMock.listPeople.mockResolvedValue(paginated([carlosPerson]));
    renderWithRouter(<PersonasPage />);

    expect(await screen.findByText("Carlos Lopez")).toBeInTheDocument();
    expect(screen.getAllByText("Sin registrar")).toHaveLength(3);
  });

  test("crea una persona y recarga el listado", async () => {
    const user = userEvent.setup();
    renderWithRouter(<PersonasPage />);
    await screen.findByText("Ana Gomez");

    await user.click(screen.getByRole("button", { name: "Nueva persona" }));
    await user.type(screen.getByLabelText("Nombre"), "  Maria  ");
    await user.type(screen.getByLabelText("Apellido"), "  Perez  ");
    await user.type(
      screen.getByLabelText("Correo electronico"),
      "maria@example.test"
    );
    await user.click(screen.getByRole("button", { name: "Crear persona" }));

    await waitFor(() =>
      expect(peopleServiceMock.createPerson).toHaveBeenCalledWith({
        first_name: "Maria",
        last_name: "Perez",
        email: "maria@example.test",
        phone_number: "",
        institutional_identifier: "",
      })
    );
    await waitFor(() =>
      expect(peopleServiceMock.listPeople).toHaveBeenCalledTimes(2)
    );
  });

  test("no crea la persona si falta un campo requerido", async () => {
    const user = userEvent.setup();
    renderWithRouter(<PersonasPage />);
    await screen.findByText("Ana Gomez");

    await user.click(screen.getByRole("button", { name: "Nueva persona" }));
    await user.type(screen.getByLabelText("Nombre"), "Maria");
    await user.click(screen.getByRole("button", { name: "Crear persona" }));

    expect(
      await screen.findByText("Complete el campo apellido.")
    ).toBeInTheDocument();
    expect(peopleServiceMock.createPerson).not.toHaveBeenCalled();
  });

  test("edita una persona con todos sus campos, sin ninguno inmutable", async () => {
    const user = userEvent.setup();
    renderWithRouter(<PersonasPage />);
    await screen.findByText("Ana Gomez");

    await user.click(screen.getByRole("button", { name: "Editar" }));
    expect(screen.getByLabelText("Nombre")).toHaveValue("Ana");

    await user.clear(screen.getByLabelText("Telefono"));
    await user.type(screen.getByLabelText("Telefono"), "50287654321");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() =>
      expect(peopleServiceMock.updatePerson).toHaveBeenCalledWith(
        "person-ana",
        {
          first_name: "Ana",
          last_name: "Gomez",
          email: "ana.gomez@example.test",
          phone_number: "50287654321",
          institutional_identifier: "INEBI-001",
        }
      )
    );
  });

  test("desactiva una persona tras confirmar", async () => {
    const user = userEvent.setup();
    renderWithRouter(<PersonasPage />);
    await screen.findByText("Ana Gomez");

    await user.click(screen.getByRole("button", { name: "Desactivar" }));
    await user.click(screen.getByRole("button", { name: "Si, desactivar" }));

    await waitFor(() =>
      expect(peopleServiceMock.deactivatePerson).toHaveBeenCalledWith(
        "person-ana"
      )
    );
  });

  test("una persona desactivada no ofrece el boton de desactivar", async () => {
    peopleServiceMock.listPeople.mockResolvedValue(paginated([carlosPerson]));
    renderWithRouter(<PersonasPage />);

    await screen.findByText("Carlos Lopez");
    expect(
      screen.queryByRole("button", { name: "Desactivar" })
    ).not.toBeInTheDocument();
  });

  test("muestra el error del listado", async () => {
    peopleServiceMock.listPeople.mockRejectedValue(
      new Error("Solicitud no completada.")
    );
    renderWithRouter(<PersonasPage />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Solicitud no completada."
    );
  });
});
