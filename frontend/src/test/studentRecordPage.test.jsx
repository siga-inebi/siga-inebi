import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("../services/studentsService.js", async () => {
  const { studentsServiceMock } = await import("./mocks/studentsService.js");
  return { studentsService: studentsServiceMock };
});

import { StudentRecordPage } from "../pages/StudentRecordPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import {
  resetStudentsServiceMock,
  studentsServiceMock,
} from "./mocks/studentsService.js";

describe("pagina puente del expediente de estudiante", () => {
  beforeEach(() => {
    resetStudentsServiceMock();
  });

  test("no monta ningun panel hasta que se abre un expediente", () => {
    renderWithRouter(<StudentRecordPage />);

    expect(
      screen.queryByText("Contactos de emergencia")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Relacion con encargados")
    ).not.toBeInTheDocument();
  });

  test("abrir un expediente monta ambos paneles con el estudiante ingresado", async () => {
    const user = userEvent.setup();
    renderWithRouter(<StudentRecordPage />);

    await user.type(
      screen.getByLabelText("Identificador del estudiante"),
      "student-1"
    );
    await user.click(screen.getByRole("button", { name: "Abrir expediente" }));

    expect(
      await screen.findByText("Contactos de emergencia")
    ).toBeInTheDocument();
    expect(screen.getByText("Relacion con encargados")).toBeInTheDocument();

    await waitFor(() =>
      expect(studentsServiceMock.listEmergencyContacts).toHaveBeenCalledWith(
        "student-1",
        { page: 1, include_inactive: false }
      )
    );
    await waitFor(() =>
      expect(
        studentsServiceMock.listStudentGuardianRelations
      ).toHaveBeenCalledWith("student-1", { page: 1, include_inactive: false })
    );
  });

  test("un identificador en blanco no abre ningun expediente", async () => {
    const user = userEvent.setup();
    renderWithRouter(<StudentRecordPage />);

    await user.click(screen.getByRole("button", { name: "Abrir expediente" }));

    expect(
      screen.queryByText("Contactos de emergencia")
    ).not.toBeInTheDocument();
    expect(studentsServiceMock.listEmergencyContacts).not.toHaveBeenCalled();
  });
});
