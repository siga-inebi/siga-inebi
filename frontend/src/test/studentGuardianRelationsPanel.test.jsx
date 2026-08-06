import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("../services/studentsService.js", async () => {
  const { studentsServiceMock } = await import("./mocks/studentsService.js");
  return { studentsService: studentsServiceMock };
});

import { StudentGuardianRelationsPanel } from "../features/students/StudentGuardianRelationsPanel.jsx";
import { paginated } from "./fixtures/academics.js";
import {
  anaGuardianOption,
  carlosGuardianOption,
  endedRelation,
  primaryRelation,
} from "./fixtures/students.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import {
  resetStudentsServiceMock,
  studentsServiceMock,
} from "./mocks/studentsService.js";

const student = { public_id: "student-1" };

describe("panel de relacion estudiante-encargado", () => {
  beforeEach(() => {
    resetStudentsServiceMock();
    studentsServiceMock.listStudentGuardianRelations.mockResolvedValue(
      paginated([primaryRelation])
    );
    studentsServiceMock.listGuardianOptions.mockResolvedValue([
      anaGuardianOption,
      carlosGuardianOption,
    ]);
  });

  test("lista la relacion vigente del estudiante recibido por prop", async () => {
    renderWithRouter(<StudentGuardianRelationsPanel student={student} />);

    expect(await screen.findByText("Ana Gomez")).toBeInTheDocument();
    expect(screen.getByText("Madre")).toBeInTheDocument();
    expect(screen.getByText("Activa")).toBeInTheDocument();
    expect(
      studentsServiceMock.listStudentGuardianRelations
    ).toHaveBeenCalledWith("student-1", { page: 1, include_inactive: false });
  });

  test("el selector solo ofrece guardianes sin relacion abierta", async () => {
    const user = userEvent.setup();
    renderWithRouter(<StudentGuardianRelationsPanel student={student} />);
    await screen.findByText("Ana Gomez");

    await user.click(
      screen.getByRole("button", { name: "Vincular encargado" })
    );

    const select = screen.getByLabelText("Encargado");
    expect(
      within(select).queryByRole("option", { name: "Ana Gomez" })
    ).not.toBeInTheDocument();
    expect(
      within(select).getByRole("option", { name: "Carlos Lopez" })
    ).toBeInTheDocument();
  });

  test("vincula un encargado existente", async () => {
    const user = userEvent.setup();
    renderWithRouter(<StudentGuardianRelationsPanel student={student} />);
    await screen.findByText("Ana Gomez");

    await user.click(
      screen.getByRole("button", { name: "Vincular encargado" })
    );
    await user.selectOptions(
      screen.getByLabelText("Encargado"),
      "guardian-carlos"
    );
    await user.type(screen.getByLabelText("Parentesco"), "Padre");
    await user.click(screen.getByRole("button", { name: "Vincular" }));

    await waitFor(() =>
      expect(
        studentsServiceMock.createStudentGuardianRelation
      ).toHaveBeenCalledWith("student-1", {
        guardian_id: "guardian-carlos",
        relationship_label: "Padre",
        is_primary: false,
      })
    );
  });

  test("editar la relacion no ofrece cambiar el encargado", async () => {
    const user = userEvent.setup();
    renderWithRouter(<StudentGuardianRelationsPanel student={student} />);
    await screen.findByText("Ana Gomez");

    await user.click(screen.getByRole("button", { name: "Editar" }));

    expect(screen.queryByLabelText("Encargado")).not.toBeInTheDocument();
    await user.clear(screen.getByLabelText("Parentesco"));
    await user.type(screen.getByLabelText("Parentesco"), "Tutora");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() =>
      expect(
        studentsServiceMock.updateStudentGuardianRelation
      ).toHaveBeenCalledWith("relation-1", {
        relationship_label: "Tutora",
        is_primary: true,
      })
    );
  });

  test("finaliza la relacion tras confirmar", async () => {
    const user = userEvent.setup();
    renderWithRouter(<StudentGuardianRelationsPanel student={student} />);
    await screen.findByText("Ana Gomez");

    await user.click(screen.getByRole("button", { name: "Finalizar" }));
    await user.click(screen.getByRole("button", { name: "Si, finalizar" }));

    await waitFor(() =>
      expect(
        studentsServiceMock.endStudentGuardianRelation
      ).toHaveBeenCalledWith("relation-1")
    );
  });

  test("una relacion ya finalizada no ofrece el boton de finalizar", async () => {
    studentsServiceMock.listStudentGuardianRelations.mockResolvedValue(
      paginated([endedRelation])
    );
    renderWithRouter(<StudentGuardianRelationsPanel student={student} />);

    await screen.findByText("Carlos Lopez");
    expect(screen.getByText("Finalizada (2025-12-31)")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Finalizar" })
    ).not.toBeInTheDocument();
  });

  test("mostrar finalizadas relee la lista con include_inactive", async () => {
    const user = userEvent.setup();
    renderWithRouter(<StudentGuardianRelationsPanel student={student} />);
    await screen.findByText("Ana Gomez");

    await user.click(screen.getByLabelText("Mostrar finalizadas"));

    await waitFor(() =>
      expect(
        studentsServiceMock.listStudentGuardianRelations
      ).toHaveBeenCalledWith("student-1", { page: 1, include_inactive: true })
    );
  });

  test("sin guardianes disponibles, deshabilita vincular y avisa", async () => {
    studentsServiceMock.listGuardianOptions.mockResolvedValue([
      anaGuardianOption,
    ]);
    renderWithRouter(<StudentGuardianRelationsPanel student={student} />);
    await screen.findByText("Ana Gomez");

    expect(
      await screen.findByText(
        "No hay encargados activos disponibles para vincular."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Vincular encargado" })
    ).toBeDisabled();
  });
});
