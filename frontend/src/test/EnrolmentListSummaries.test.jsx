import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

const get = vi.hoisted(() => vi.fn());
vi.mock("@shared/api/apiClient.js", () => ({ apiClient: { get } }));

import { EnrolmentsPage } from "@enrolments/EnrolmentsPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const ROW = {
  public_id: "enrolment-1",
  student_id: "student-1",
  academic_cycle_id: "cycle-1",
  grade_id: "grade-1",
  section_id: "section-1",
  status: "active",
  effective_on: "2026-01-15",
  student: {
    public_id: "student-1",
    full_name: "Alumno Demo",
    student_code: "EST-DEMO",
  },
  academic_cycle: { public_id: "cycle-1", name: "Ciclo demo" },
  grade: { public_id: "grade-1", name: "Primero" },
  section: {
    public_id: "section-1",
    name: "A",
    grade_name: "Primero",
    shift_name: "Matutina",
  },
};
const page = (results, count = results.length) => ({
  count,
  results,
  next: null,
  previous: null,
});
const enrolmentCalls = () =>
  get.mock.calls.filter(([url]) => url.startsWith("/enrolments/"));

beforeEach(() => {
  get.mockReset();
  get.mockImplementation(async (url) =>
    url.startsWith("/enrolments/active/") ? page([ROW]) : page([])
  );
});

test("renders embedded labels with only the enrolment request", async () => {
  renderWithRouter(<EnrolmentsPage />);
  expect(await screen.findByText("Alumno Demo · EST-DEMO")).toBeInTheDocument();
  expect(screen.getByText("Ciclo demo")).toBeInTheDocument();
  expect(screen.getByText("Primero A · Matutina")).toBeInTheDocument();
  expect(enrolmentCalls()).toHaveLength(1);
  expect(enrolmentCalls()[0][0]).toMatch(/^\/enrolments\/active\//);
  expect(screen.queryByText("student-1")).not.toBeInTheDocument();
});

test("requests only the visible enrolment page", async () => {
  get.mockImplementation(async (url) =>
    url.includes("page=2")
      ? page(
          [
            {
              ...ROW,
              public_id: "enrolment-2",
              student: { ...ROW.student, full_name: "Segunda Demo" },
            },
          ],
          26
        )
      : page([ROW], 26)
  );
  const user = userEvent.setup();
  renderWithRouter(<EnrolmentsPage />);
  await screen.findByText("Alumno Demo · EST-DEMO");
  await user.click(screen.getByRole("button", { name: "Siguiente" }));
  expect(
    await screen.findByText("Segunda Demo · EST-DEMO")
  ).toBeInTheDocument();
  expect(enrolmentCalls()).toHaveLength(2);
  expect(enrolmentCalls()[1][0]).toContain("page=2");
});

test("searches students remotely and loads history only after selection", async () => {
  get.mockImplementation(async (url) => {
    if (url.startsWith("/students/"))
      return page([
        {
          public_id: "student-1",
          person: { first_name: "Alumno", last_name: "Demo" },
          student_code: "EST-DEMO",
        },
      ]);
    return page([ROW]);
  });
  const user = userEvent.setup();
  renderWithRouter(<EnrolmentsPage />);
  await screen.findByText("Alumno Demo · EST-DEMO");
  await user.click(screen.getByRole("tab", { name: /Historial/ }));
  expect(
    get.mock.calls.some(([url]) => url.startsWith("/enrolments/history/"))
  ).toBe(false);
  const picker = screen.getByRole("combobox", { name: "Estudiante" });
  await user.type(picker, "Alumno");
  await user.click(
    await screen.findByRole("option", { name: "Alumno Demo · EST-DEMO" })
  );
  await waitFor(() =>
    expect(
      get.mock.calls.some(
        ([url]) =>
          url.startsWith("/enrolments/history/") &&
          url.includes("student_id=student-1")
      )
    ).toBe(true)
  );
  const searches = get.mock.calls.filter(([url]) =>
    url.startsWith("/students/")
  );
  expect(searches).toHaveLength(1);
  expect(searches[0][0]).toContain("search=Alumno");
  expect(searches[0][0]).toContain("include_inactive=true");
  expect(picker).toHaveValue("Alumno Demo · EST-DEMO");
  await user.click(screen.getByRole("button", { name: "Limpiar" }));
  expect(
    screen.getByText(/elija uno en el filtro de arriba/)
  ).toBeInTheDocument();
  expect(picker).toHaveValue("");
});

test("defers creation catalogues until the user opens the form", async () => {
  const user = userEvent.setup();
  renderWithRouter(<EnrolmentsPage />);
  await screen.findByText("Alumno Demo · EST-DEMO");
  expect(enrolmentCalls()).toHaveLength(1);
  expect(get.mock.calls.some(([url]) => url.startsWith("/students/"))).toBe(
    false
  );
  expect(
    get.mock.calls.some(([url]) => url.startsWith("/academics/sections/"))
  ).toBe(false);
  await user.click(screen.getByRole("button", { name: "Matricular" }));
  await user.click(screen.getByRole("menuitem", { name: /Un estudiante/ }));
  const dialog = await screen.findByRole("dialog", {
    name: "Matricular estudiante",
  });
  expect(
    within(dialog).getByRole("button", { name: "Confirmar matrícula" })
  ).toBeInTheDocument();
  await waitFor(() =>
    expect(
      get.mock.calls.some(([url]) => url.startsWith("/academics/sections/"))
    ).toBe(true)
  );
  expect(get.mock.calls.some(([url]) => url.startsWith("/students/"))).toBe(
    true
  );
});
