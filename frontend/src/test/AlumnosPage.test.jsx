import { Route, Routes } from "react-router-dom";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { AlumnosPage } from "@students/AlumnosPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import {
  fillInstitutionalPerson,
  institutionalPerson,
  visibleInstitutionalPerson,
} from "./helpers/institutionalPerson.js";

const studentsServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  // Ver el doble homonimo en DocentesPage.test.jsx: el alta pide el codigo
  // sugerido al abrir, y sin esto la prueba corre por el camino de error.
  nextCode: vi.fn(),
  listHealthNotes: vi.fn(),
  createHealthNote: vi.fn(),
  listObservations: vi.fn(),
  createObservation: vi.fn(),
  listEmergencyContacts: vi.fn(),
  createEmergencyContact: vi.fn(),
  listGuardianRelations: vi.fn(),
  createGuardianRelation: vi.fn(),
}));

const guardiansServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
}));

vi.mock("@students/studentsService.js", () => ({
  studentsService: studentsServiceMock,
}));

vi.mock("@guardians/guardiansService.js", () => ({
  guardiansService: guardiansServiceMock,
}));

const downloadCsvMock = vi.hoisted(() => vi.fn());

vi.mock("@shared/utils/csv.js", () => ({ downloadCsv: downloadCsvMock }));

const SAMPLE = [
  {
    id: 1,
    public_id: "student-1",
    person: {
      ...visibleInstitutionalPerson,
      public_id: "person-11",
      first_name: "Maria Jose",
      last_name: "Lopez Garcia",
      email: "maria@example.test",
      phone_number: "555-0101",
    },
    student_code: "EST-2026-014",
    status: "active",
    photo: "http://localhost/media/student_photos/maria.png",
  },
  {
    id: 2,
    public_id: "student-2",
    person: {
      public_id: "person-12",
      first_name: "Carlos Enrique",
      last_name: "Ramirez Perez",
      email: "carlos@example.test",
      phone_number: "555-0102",
    },
    student_code: "EST-2026-015",
    status: "active",
    photo: "",
  },
];

describe("AlumnosPage", () => {
  beforeEach(() => {
    studentsServiceMock.list.mockReset();
    studentsServiceMock.create.mockReset();
    studentsServiceMock.update.mockReset();
    studentsServiceMock.listHealthNotes.mockReset();
    studentsServiceMock.createHealthNote.mockReset();
    studentsServiceMock.listHealthNotes.mockResolvedValue([]);
    studentsServiceMock.listObservations.mockReset();
    studentsServiceMock.createObservation.mockReset();
    studentsServiceMock.listObservations.mockResolvedValue([]);
    studentsServiceMock.listEmergencyContacts.mockReset();
    studentsServiceMock.createEmergencyContact.mockReset();
    studentsServiceMock.listEmergencyContacts.mockResolvedValue([]);
    studentsServiceMock.listGuardianRelations.mockReset();
    studentsServiceMock.createGuardianRelation.mockReset();
    studentsServiceMock.listGuardianRelations.mockResolvedValue([]);
    guardiansServiceMock.list.mockReset();
    downloadCsvMock.mockReset();
  });

  test("exports the currently filtered rows as CSV", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: "Exportar CSV" }));

    expect(downloadCsvMock).toHaveBeenCalledTimes(1);
    const [filename, , rows] = downloadCsvMock.mock.calls[0];
    expect(filename).toBe("alumnos.csv");
    expect(rows).toEqual(SAMPLE);
  });

  test("renders the list once loaded", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    renderWithRouter(<AlumnosPage />);

    expect(
      await screen.findByText("Maria Jose Lopez Garcia")
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("table")).getByText("EST-2026-014")
    ).toBeInTheDocument();
    expect(screen.getByText(/Mostrando 1–2 de 2/)).toBeInTheDocument();
  });

  test("shows an empty state when the search does not match", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.type(screen.getByPlaceholderText("Buscar por nombre…"), "Nadie");

    expect(
      await screen.findByText("Sin resultados para la busqueda.")
    ).toBeInTheDocument();
  });

  test("shows the service error instead of the table", async () => {
    studentsServiceMock.list.mockRejectedValue(
      new Error("Solicitud no completada.")
    );
    renderWithRouter(<AlumnosPage />);

    expect(
      await screen.findByText("Solicitud no completada.")
    ).toBeInTheDocument();
  });

  test("submits the create form against the mock service and reloads the list", async () => {
    const createdStudent = {
      id: 3,
      person: {
        public_id: "person-13",
        first_name: "Nueva",
        last_name: "Alumna",
        email: "nueva@example.test",
        phone_number: "555-0199",
      },
      student_code: "EST-2026-099",
      status: "pre_enrolled",
      photo: "",
    };
    studentsServiceMock.list
      .mockResolvedValueOnce(SAMPLE)
      .mockResolvedValueOnce([...SAMPLE, createdStudent]);
    studentsServiceMock.nextCode.mockResolvedValue("EST-2026-0101");
    studentsServiceMock.create.mockResolvedValue(createdStudent);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: /Nuevo estudiante/ }));

    await user.type(screen.getByLabelText(/^Nombres/), "Nueva");
    await user.type(screen.getByLabelText(/^Apellidos/), "Alumna");
    await fillInstitutionalPerson(user);
    await user.type(screen.getByLabelText(/^Correo/), "nueva@example.test");
    const codeField = screen.getByLabelText(/^Codigo de estudiante/);
    // Llega prellenado con la sugerencia del backend, y se puede sobreescribir:
    // un traslado trae su codigo ya impreso en los papeles.
    expect(codeField).toHaveValue("EST-2026-0101");
    await user.clear(codeField);
    await user.type(codeField, "EST-2026-099");
    await user.click(screen.getByRole("button", { name: /Crear estudiante/ }));

    await waitFor(() =>
      expect(studentsServiceMock.create).toHaveBeenCalledTimes(1)
    );
    expect(studentsServiceMock.create).toHaveBeenCalledWith(
      expect.objectContaining({
        person: {
          ...institutionalPerson,
          first_name: "Nueva",
          last_name: "Alumna",
          email: "nueva@example.test",
          phone_number: "555-0199",
        },
        student_code: "EST-2026-099",
        status: "pre_enrolled",
      })
    );
    await waitFor(() =>
      expect(studentsServiceMock.list).toHaveBeenCalledTimes(2)
    );
    expect(await screen.findByText("Nueva Alumna")).toBeInTheDocument();
    // Ver el presupuesto homonimo en DocentesPage.test.jsx.
  }, 15000);

  test("previews a newly selected photo in the create form", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: /Nuevo estudiante/ }));

    expect(screen.queryByAltText("Vista previa")).not.toBeInTheDocument();

    const file = new File(["fake-image-bytes"], "avatar.png", {
      type: "image/png",
    });
    await user.upload(screen.getByLabelText(/^Foto/), file);

    expect(await screen.findByAltText("Vista previa")).toHaveAttribute(
      "src",
      "blob:mock-url"
    );
  });

  test("requires the mandatory fields before submitting", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: /Nuevo estudiante/ }));
    await user.click(screen.getByRole("button", { name: /Crear estudiante/ }));

    expect(screen.getByText(/Complete el campo/)).toBeInTheDocument();
    expect(studentsServiceMock.create).not.toHaveBeenCalled();
  });

  test("abre el expediente desde el listado mediante una ruta propia", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(
      <Routes>
        <Route path="/" element={<AlumnosPage />} />
        <Route
          path="/app/alumnos/:studentId"
          element={<p>Expediente abierto</p>}
        />
      </Routes>
    );
    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);
    expect(await screen.findByText("Expediente abierto")).toBeInTheDocument();
  });
});
