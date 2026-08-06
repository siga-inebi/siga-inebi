import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("../services/studentsService.js", async () => {
  const { studentsServiceMock } = await import("./mocks/studentsService.js");
  return { studentsService: studentsServiceMock };
});

import { EmergencyContactsPanel } from "../features/students/EmergencyContactsPanel.jsx";
import { paginated } from "./fixtures/academics.js";
import { auntContact, inactiveContact } from "./fixtures/students.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import {
  resetStudentsServiceMock,
  studentsServiceMock,
} from "./mocks/studentsService.js";

const student = { public_id: "student-1" };

describe("panel de contactos de emergencia", () => {
  beforeEach(() => {
    resetStudentsServiceMock();
    studentsServiceMock.listEmergencyContacts.mockResolvedValue(
      paginated([auntContact])
    );
  });

  test("lista los contactos del estudiante recibido por prop", async () => {
    renderWithRouter(<EmergencyContactsPanel student={student} />);

    expect(await screen.findByText("Maria Perez")).toBeInTheDocument();
    expect(studentsServiceMock.listEmergencyContacts).toHaveBeenCalledWith(
      "student-1",
      { page: 1, include_inactive: false }
    );
  });

  test("agrega un contacto y recarga el listado", async () => {
    const user = userEvent.setup();
    renderWithRouter(<EmergencyContactsPanel student={student} />);
    await screen.findByText("Maria Perez");

    await user.click(screen.getByRole("button", { name: "Nuevo contacto" }));
    await user.type(screen.getByLabelText("Nombre"), "Luisa Diaz");
    await user.type(screen.getByLabelText("Telefono"), "555-0200");
    await user.type(screen.getByLabelText("Parentesco"), "Abuela");
    await user.click(screen.getByRole("button", { name: "Agregar contacto" }));

    await waitFor(() =>
      expect(studentsServiceMock.createEmergencyContact).toHaveBeenCalledWith(
        "student-1",
        {
          name: "Luisa Diaz",
          phone_number: "555-0200",
          relationship_label: "Abuela",
        }
      )
    );
    await waitFor(() =>
      expect(studentsServiceMock.listEmergencyContacts).toHaveBeenCalledTimes(2)
    );
  });

  test("quita un contacto tras confirmar", async () => {
    const user = userEvent.setup();
    renderWithRouter(<EmergencyContactsPanel student={student} />);
    await screen.findByText("Maria Perez");

    await user.click(screen.getByRole("button", { name: "Quitar" }));
    await user.click(screen.getByRole("button", { name: "Si, quitar" }));

    await waitFor(() =>
      expect(
        studentsServiceMock.deactivateEmergencyContact
      ).toHaveBeenCalledWith("contact-1")
    );
  });

  test("mostrar quitados relee la lista con include_inactive", async () => {
    const user = userEvent.setup();
    studentsServiceMock.listEmergencyContacts.mockResolvedValue(
      paginated([auntContact, inactiveContact])
    );
    renderWithRouter(<EmergencyContactsPanel student={student} />);
    await screen.findByText("Maria Perez");

    await user.click(screen.getByLabelText("Mostrar quitados"));

    await waitFor(() =>
      expect(studentsServiceMock.listEmergencyContacts).toHaveBeenCalledWith(
        "student-1",
        { page: 1, include_inactive: true }
      )
    );
    expect(await screen.findByText("Jose Ramirez")).toBeInTheDocument();
  });
});
