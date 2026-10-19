import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { AlumnosPage } from "@students/AlumnosPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const service = vi.hoisted(() => ({
  list: vi.fn(),
  listGuardianRelations: vi.fn(),
  listHealthNotes: vi.fn(),
  listObservations: vi.fn(),
  listEmergencyContacts: vi.fn(),
  createHealthNote: vi.fn(),
}));
vi.mock("@students/studentsService.js", () => ({ studentsService: service }));
vi.mock("@guardians/guardiansService.js", () => ({
  guardiansService: { list: vi.fn() },
}));

const FIRST = "11111111-1111-1111-1111-111111111111";
const SECOND = "22222222-2222-2222-2222-222222222222";
const EMPTY = { results: [], count: 0, next: null, previous: null };
const STUDENTS = [
  {
    id: 1,
    public_id: FIRST,
    person: { first_name: "Ana", last_name: "Demo" },
    status: "active",
  },
  {
    id: 2,
    public_id: SECOND,
    person: { first_name: "Beto", last_name: "Demo" },
    status: "active",
  },
];
const guardian = (id, name) => ({
  id,
  guardian_detail: { person: { first_name: name, last_name: "Demo" } },
  relationship_label: "Responsable",
  is_primary: false,
});

beforeEach(() => {
  for (const mock of Object.values(service)) mock.mockReset();
  service.list.mockResolvedValue(STUDENTS);
  for (const name of [
    "listGuardianRelations",
    "listHealthNotes",
    "listObservations",
    "listEmergencyContacts",
  ]) {
    service[name].mockResolvedValue(EMPTY);
  }
});

async function openStudent(user, index = 0) {
  await screen.findByText("Ana Demo");
  await user.click(
    screen.getAllByRole("button", { name: /Ver detalle/ })[index]
  );
}

test("guardian pages are requested for the selected student's public_id", async () => {
  service.listGuardianRelations.mockImplementation(async (_id, { page }) => ({
    count: 26,
    results:
      page === 1
        ? [guardian(1, "Encargado inicial")]
        : [guardian(26, "Encargado final")],
  }));
  const user = userEvent.setup();
  renderWithRouter(<AlumnosPage />);
  await openStudent(user);
  await screen.findByText("Encargado inicial Demo");
  expect(service.listGuardianRelations).toHaveBeenCalledWith(FIRST, {
    page: 1,
  });
  await user.click(screen.getByRole("button", { name: "Ir a la página 2" }));
  expect(await screen.findByText("Encargado final Demo")).toBeInTheDocument();
  expect(service.listGuardianRelations).toHaveBeenLastCalledWith(FIRST, {
    page: 2,
  });
  expect(screen.queryByText("Encargado inicial Demo")).not.toBeInTheDocument();
});

test.each([
  [
    "Salud",
    "listHealthNotes",
    (id, text) => ({
      public_id: id,
      content: text,
      author: "Demo",
      recorded_on: "2026-10-17",
    }),
  ],
  [
    "Observaciones",
    "listObservations",
    (id, text) => ({
      public_id: id,
      description: text,
      author: "Demo",
      observed_on: "2026-10-17",
    }),
  ],
  [
    "Contactos de emergencia",
    "listEmergencyContacts",
    (id, text) => ({
      public_id: id,
      name: text,
      phone_number: "5550000",
      relationship_label: "Responsable",
    }),
  ],
])(
  "%s fetches page two only when requested",
  async (button, method, makeRecord) => {
    service[method].mockImplementation(async (_id, { page }) => ({
      count: 26,
      results: [
        makeRecord(
          String(page),
          page === 1 ? "Registro inicial" : "Registro final"
        ),
      ],
    }));
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);
    await openStudent(user);
    await user.click(screen.getByRole("button", { name: button }));
    expect(await screen.findByText(/Registro inicial/)).toBeInTheDocument();
    expect(service[method]).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("button", { name: "Ir a la página 2" }));
    expect(await screen.findByText(/Registro final/)).toBeInTheDocument();
    expect(service[method]).toHaveBeenLastCalledWith(FIRST, { page: 2 });
    expect(screen.queryByText(/Registro inicial/)).not.toBeInTheDocument();
  }
);

test("a failed page can be retried without showing an empty record list", async () => {
  service.listGuardianRelations
    .mockResolvedValueOnce({ count: 26, results: [guardian(1, "Inicial")] })
    .mockRejectedValueOnce(new Error("Error de conexión"))
    .mockResolvedValue({ count: 26, results: [guardian(26, "Recuperado")] });
  const user = userEvent.setup();
  renderWithRouter(<AlumnosPage />);
  await openStudent(user);
  await screen.findByText("Inicial Demo");
  await user.click(screen.getByRole("button", { name: "Ir a la página 2" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Error de conexión"
  );
  expect(
    screen.queryByText("Sin encargados vinculados")
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Reintentar" }));
  expect(await screen.findByText("Recuperado Demo")).toBeInTheDocument();
  expect(service.listGuardianRelations).toHaveBeenLastCalledWith(FIRST, {
    page: 2,
  });
});

test("a late response from a previous student cannot replace the current relations", async () => {
  let finishFirst;
  service.listGuardianRelations.mockImplementation((id) =>
    id === FIRST
      ? new Promise((resolve) => {
          finishFirst = resolve;
        })
      : Promise.resolve({ count: 1, results: [guardian(2, "Actual")] })
  );
  const user = userEvent.setup();
  renderWithRouter(<AlumnosPage />);
  await openStudent(user);
  await waitFor(() => expect(finishFirst).toBeTypeOf("function"));
  await user.click(
    within(screen.getByRole("dialog")).getByRole("button", { name: /Cerrar/ })
  );
  await waitFor(() =>
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  );
  await openStudent(user, 1);
  await screen.findByText("Actual Demo");
  await act(async () =>
    finishFirst({ count: 1, results: [guardian(1, "Anterior")] })
  );
  expect(screen.queryByText("Anterior Demo")).not.toBeInTheDocument();
  expect(screen.getByText("Actual Demo")).toBeInTheDocument();
});

test("records beyond the first thousand remain reachable without downloading other pages", async () => {
  service.listGuardianRelations.mockImplementation(async (_id, { page }) => ({
    count: 1001,
    results: [guardian(page, page === 41 ? "Ultimo" : "Primero")],
  }));
  const user = userEvent.setup();
  renderWithRouter(<AlumnosPage />);
  await openStudent(user);
  await screen.findByText("Primero Demo");
  await user.click(screen.getByRole("button", { name: "Ir a la página 41" }));
  expect(await screen.findByText("Ultimo Demo")).toBeInTheDocument();
  expect(service.listGuardianRelations).toHaveBeenCalledTimes(2);
  expect(service.listGuardianRelations).toHaveBeenLastCalledWith(FIRST, {
    page: 41,
  });
});

test("creating a note from page two refreshes the first page and its total", async () => {
  let created = false;
  service.createHealthNote.mockImplementation(async () => {
    created = true;
    return {};
  });
  service.listHealthNotes.mockImplementation(async (_id, { page }) => ({
    count: created ? 27 : 26,
    results: [
      {
        public_id: "note-" + page,
        recorded_on: "2026-10-17",
        author: "Demo",
        content: created ? "Nueva nota registrada" : "Nota anterior " + page,
      },
    ],
  }));
  const user = userEvent.setup();
  renderWithRouter(<AlumnosPage />);
  await openStudent(user);
  await user.click(screen.getByRole("button", { name: "Salud" }));
  await screen.findByText("Nota anterior 1");
  await user.click(screen.getByRole("button", { name: "Ir a la página 2" }));
  await screen.findByText("Nota anterior 2");
  await user.click(screen.getByRole("button", { name: "Nueva nota" }));
  await user.type(screen.getByLabelText(/^Información de salud/), "Nueva");
  await user.click(screen.getByRole("button", { name: "Registrar nota" }));
  expect(await screen.findByText("Nueva nota registrada")).toBeInTheDocument();
  expect(service.listHealthNotes).toHaveBeenLastCalledWith(FIRST, { page: 1 });
  expect(screen.getByText(/27 registros/)).toBeInTheDocument();
});
