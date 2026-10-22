import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

const services = vi.hoisted(() => ({
  student: vi.fn(),
  teacher: vi.fn(),
  guardian: vi.fn(),
  positions: vi.fn(),
}));

vi.mock("@students/studentsService.js", () => ({
  studentsService: { create: services.student },
}));
vi.mock("@teachers/teachersService.js", () => ({
  teachersService: {
    create: services.teacher,
    listPositions: services.positions,
  },
}));
vi.mock("@guardians/guardiansService.js", () => ({
  guardiansService: { create: services.guardian },
}));

import { PersonConversionWindow } from "@people/PersonConversionWindow.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import { selectOption } from "./helpers/selectOption.jsx";

beforeEach(() => {
  vi.clearAllMocks();
  services.student.mockResolvedValue({});
  services.teacher.mockResolvedValue({});
  services.guardian.mockResolvedValue({});
  services.positions.mockResolvedValue([
    { value: "Docente Titulado", label: "Docente Titulado" },
  ]);
});

test("convierte una persona existente en estudiante sin crear otra persona", async () => {
  const user = userEvent.setup();
  const onConverted = vi.fn();
  renderWithRouter(
    <PersonConversionWindow
      person={{
        public_id: "persona-1",
        first_name: "Ana",
        last_name: "Gomez",
        phone_number: "55500000",
        profiles: {},
      }}
      onCancel={vi.fn()}
      onConverted={onConverted}
    />
  );

  fireEvent.change(screen.getByLabelText(/^CUI/), {
    target: { value: "1234567890123" },
  });
  fireEvent.change(screen.getByLabelText(/^Fecha de nacimiento/), {
    target: { value: "2001-05-20" },
  });
  await selectOption(user, /^Sexo/, "Femenino");
  fireEvent.change(screen.getByLabelText(/^Dirección/), {
    target: { value: "Direccion" },
  });
  fireEvent.change(screen.getByLabelText(/^Departamento/), {
    target: { value: "Guatemala" },
  });
  fireEvent.change(screen.getByLabelText(/^Municipio/), {
    target: { value: "Guatemala" },
  });
  await user.click(screen.getByRole("button", { name: "Crear perfil" }));

  await waitFor(() =>
    expect(services.student).toHaveBeenCalledWith(
      expect.objectContaining({
        person_public_id: "persona-1",
        person: expect.objectContaining({
          first_name: "Ana",
          last_name: "Gomez",
          cui: "1234567890123",
        }),
      })
    )
  );
  expect(onConverted).toHaveBeenCalledOnce();
  expect(services.teacher).not.toHaveBeenCalled();
  expect(services.guardian).not.toHaveBeenCalled();
});
