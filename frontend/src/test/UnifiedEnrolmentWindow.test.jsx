import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

const register = vi.hoisted(() => vi.fn());
const listSectionOccupancy = vi.hoisted(() => vi.fn());
vi.mock("@enrolments/enrolmentsService.js", () => ({
  enrolmentsService: { listSectionOccupancy, register },
}));
vi.mock("@shared/catalogs/academicCatalogs.js", () => ({
  useStudentCatalog: () => ({
    options: [{ value: "s1", label: "Alumno Demo" }],
  }),
  useCycleCatalog: () => ({ options: [{ value: "c1", label: "Ciclo Demo" }] }),
  useSectionCatalog: () => ({
    options: [
      { value: "a1", label: "Seccion A", gradeId: "g1", shiftId: "j1" },
    ],
  }),
  sectionsForCycle: (options, cycle) => (cycle ? options : []),
}));

import { EnrolmentCreateWindow } from "@enrolments/EnrolmentCreateWindow.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

beforeEach(() => {
  register.mockReset();
  listSectionOccupancy.mockReset().mockResolvedValue({
    count: 1,
    results: [
      {
        public_id: "a1",
        academic_cycle_id: "c1",
        capacity: 30,
        occupied_seats: 10,
        available_seats: 20,
      },
    ],
  });
});

async function fill(user) {
  for (const [name, option] of [
    ["Estudiante", "Alumno Demo"],
    ["Ciclo escolar", "Ciclo Demo"],
    ["Seccion", "Seccion A"],
  ]) {
    await user.click(screen.getByRole("combobox", { name }));
    await user.click(await screen.findByRole("option", { name: option }));
  }
  await user.type(screen.getByLabelText(/Vigente desde/), "2027-02-01");
}

test("un rechazo conserva datos y reintentar hace solo la escritura unificada", async () => {
  register.mockRejectedValueOnce(new Error("La seccion no tiene vacantes."));
  register.mockResolvedValueOnce({ registration_mode: "reenrolment" });
  const onCreated = vi.fn();
  const user = userEvent.setup();
  renderWithRouter(
    <EnrolmentCreateWindow onCancel={vi.fn()} onCreated={onCreated} />
  );
  await fill(user);
  await user.click(screen.getByRole("button", { name: "Confirmar matrícula" }));
  expect(
    await screen.findByText("La seccion no tiene vacantes.")
  ).toBeInTheDocument();
  expect(screen.getByLabelText(/Vigente desde/)).toHaveValue("2027-02-01");
  expect(
    screen.getByRole("combobox", { name: "Estudiante" })
  ).toHaveTextContent("Alumno Demo");
  expect(onCreated).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Confirmar matrícula" }));
  await waitFor(() => expect(onCreated).toHaveBeenCalledTimes(1));
  expect(register).toHaveBeenCalledTimes(2);
  expect(register).toHaveBeenLastCalledWith({
    student_id: "s1",
    academic_cycle_id: "c1",
    section_id: "a1",
    grade_id: "g1",
    shift_id: "j1",
    effective_on: "2027-02-01",
  });
});

test("mientras confirma bloquea nuevos envios y no ejecuta el cierre exitoso", async () => {
  let finish;
  register.mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      })
  );
  const onCreated = vi.fn();
  const user = userEvent.setup();
  renderWithRouter(
    <EnrolmentCreateWindow onCancel={vi.fn()} onCreated={onCreated} />
  );
  await fill(user);
  await user.click(screen.getByRole("button", { name: "Confirmar matrícula" }));
  expect(screen.getByRole("button", { name: /Guardando/ })).toBeDisabled();
  expect(onCreated).not.toHaveBeenCalled();
  expect(register).toHaveBeenCalledTimes(1);
  finish({ registration_mode: "matriculation" });
  await waitFor(() => expect(onCreated).toHaveBeenCalledTimes(1));
});
