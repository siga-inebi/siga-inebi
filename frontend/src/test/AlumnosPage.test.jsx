import { Route, Routes, useLocation } from "react-router-dom";
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
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
  listPage: vi.fn(),
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

vi.mock("@shared/utils/csv.js", async (importOriginal) => ({
  ...(await importOriginal()),
  triggerCsvDownload: downloadCsvMock,
}));

const paged = (results, count = results.length, next = null) => ({
  results,
  count,
  next,
  previous: null,
});

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{JSON.stringify(location)}</output>;
}

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
    studentsServiceMock.listPage.mockReset().mockResolvedValue(paged(SAMPLE));
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

  test("pide solo la página visible y recupera filtros y tamaño desde la URL", async () => {
    studentsServiceMock.listPage.mockResolvedValue(paged(SAMPLE, 2500));
    renderWithRouter(<AlumnosPage />, {
      route:
        "/app/alumnos?page=2&page_size=50&search=EST-2026&status=active&include_inactive=1",
    });
    await screen.findByText("Maria Jose Lopez Garcia");
    expect(studentsServiceMock.listPage).toHaveBeenCalledExactlyOnceWith({
      page: 2,
      page_size: 50,
      search: "EST-2026",
      status: "active",
      include_inactive: true,
    });
    expect(studentsServiceMock.list).not.toHaveBeenCalled();
    expect(
      screen.getByText(/2500 estudiantes encontrados/)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("switch", { name: "Mostrar desactivados" })
    ).toBeChecked();
  });

  test("pagina y cambia tamaño sin descargar el padrón completo", async () => {
    studentsServiceMock.listPage.mockResolvedValue(paged(SAMPLE, 2500));
    const user = userEvent.setup();
    renderWithRouter(
      <>
        <AlumnosPage />
        <LocationProbe />
      </>
    );
    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await waitFor(() =>
      expect(studentsServiceMock.listPage).toHaveBeenLastCalledWith({
        page: 2,
        page_size: 25,
      })
    );
    await user.click(
      screen.getByRole("combobox", { name: /Filas por página/ })
    );
    await user.click(screen.getByRole("option", { name: "50", exact: true }));
    await waitFor(() =>
      expect(studentsServiceMock.listPage).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 50,
      })
    );
    expect(JSON.parse(screen.getByTestId("location").textContent).search).toBe(
      "?page_size=50"
    );
    expect(studentsServiceMock.list).not.toHaveBeenCalled();
  });

  test("combina búsqueda por código, estado y desactivados en el servidor", async () => {
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />, { route: "/app/alumnos?page=2" });
    await screen.findByText("Maria Jose Lopez Garcia");
    await user.type(
      screen.getByPlaceholderText(/Buscar por nombre/),
      "EST-2026"
    );
    expect(screen.getByRole("button", { name: "Exportar CSV" })).toBeDisabled();
    await waitFor(() =>
      expect(studentsServiceMock.listPage).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 25,
        search: "EST-2026",
      })
    );
    await user.click(
      screen.getByRole("combobox", { name: "Estado del expediente" })
    );
    await user.click(
      screen.getByRole("option", { name: "Activo", exact: true })
    );
    await user.click(
      screen.getByRole("switch", { name: "Mostrar desactivados" })
    );
    await waitFor(() =>
      expect(studentsServiceMock.listPage).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 25,
        search: "EST-2026",
        status: "active",
        include_inactive: true,
      })
    );
    expect(
      await screen.findByText("Maria Jose Lopez Garcia")
    ).toBeInTheDocument();
  });

  test("exporta más de mil resultados filtrados solo al solicitarlo", async () => {
    const rows = Array.from({ length: 1001 }, (_, index) => ({
      ...SAMPLE[0],
      id: index + 1,
      public_id: `student-${index + 1}`,
      student_code: `DEMO-${index + 1}`,
    }));
    studentsServiceMock.listPage.mockImplementation(
      async ({ page, page_size }) =>
        paged(
          rows.slice((page - 1) * page_size, page * page_size),
          rows.length,
          page * page_size < rows.length ? "next" : null
        )
    );
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />, {
      route: "/app/alumnos?search=DEMO&status=active&include_inactive=1&page=2",
    });
    await screen.findByText("DEMO-26");
    expect(studentsServiceMock.listPage).toHaveBeenCalledTimes(1);
    expect(downloadCsvMock).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Exportar CSV" }));
    await waitFor(() => expect(downloadCsvMock).toHaveBeenCalledTimes(1));
    const [filename, csv] = downloadCsvMock.mock.calls[0];
    expect(filename).toBe("alumnos.csv");
    expect(csv).toContain("DEMO-1");
    expect(csv).toContain("DEMO-1001");
    expect(csv.trim().split(/\r?\n/)).toHaveLength(1002);
    const calls = studentsServiceMock.listPage.mock.calls.slice(1);
    expect(calls).toHaveLength(11);
    calls.forEach(([params], index) =>
      expect(params).toEqual({
        search: "DEMO",
        status: "active",
        include_inactive: true,
        page: index + 1,
        page_size: 100,
      })
    );
  });

  test("renders the list once loaded", async () => {
    studentsServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
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
    studentsServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    studentsServiceMock.listPage.mockResolvedValue(paged([]));
    await user.type(screen.getByPlaceholderText(/Buscar por nombre/), "Nadie");

    expect(
      await screen.findByText("Sin estudiantes para los filtros seleccionados.")
    ).toBeInTheDocument();
  });

  test("shows the service error instead of the table", async () => {
    studentsServiceMock.listPage.mockRejectedValue(
      new Error("Solicitud no completada.")
    );
    renderWithRouter(<AlumnosPage />);

    expect(
      await screen.findByText("Solicitud no completada.")
    ).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    studentsServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Reintentar" }));
    expect(
      await screen.findByText("Maria Jose Lopez Garcia")
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
    studentsServiceMock.listPage
      .mockResolvedValueOnce(paged(SAMPLE))
      .mockResolvedValueOnce(paged([...SAMPLE, createdStudent]));
    studentsServiceMock.nextCode.mockResolvedValue("EST-2026-0101");
    studentsServiceMock.create.mockResolvedValue(createdStudent);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: /Nuevo estudiante/ }));

    // Ver el comentario homonimo en DocentesPage.test.jsx: un `change` por
    // campo y etiquetas buscadas dentro del dialogo.
    const dialog = screen.getByRole("dialog");
    const form = within(dialog);
    const fill = (label, value) =>
      fireEvent.change(form.getByLabelText(label), { target: { value } });
    fill(/^Nombres/, "Nueva");
    fill(/^Apellidos/, "Alumna");
    await fillInstitutionalPerson(user, dialog);
    fill(/^Correo/, "nueva@example.test");
    // Llega prellenado con la sugerencia del backend, y se puede sobreescribir:
    // un traslado trae su codigo ya impreso en los papeles.
    expect(form.getByLabelText(/^Codigo de estudiante/)).toHaveValue(
      "EST-2026-0101"
    );
    fill(/^Codigo de estudiante/, "EST-2026-099");
    await user.click(form.getByRole("button", { name: /Crear estudiante/ }));

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
      expect(studentsServiceMock.listPage).toHaveBeenCalledTimes(2)
    );
    expect(await screen.findByText("Nueva Alumna")).toBeInTheDocument();
  });

  test("previews a newly selected photo in the create form", async () => {
    studentsServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
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
    studentsServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: /Nuevo estudiante/ }));
    await user.click(screen.getByRole("button", { name: /Crear estudiante/ }));

    expect(screen.getByText(/Complete el campo/)).toBeInTheDocument();
    expect(studentsServiceMock.create).not.toHaveBeenCalled();
  });

  test("abre el expediente desde el listado mediante una ruta propia", async () => {
    studentsServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
    const user = userEvent.setup();
    renderWithRouter(
      <Routes>
        <Route path="/" element={<AlumnosPage />} />
        <Route
          path="/app/alumnos/:studentId"
          element={
            <>
              <p>Expediente abierto</p>
              <LocationProbe />
            </>
          }
        />
      </Routes>
    );
    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);
    expect(await screen.findByText("Expediente abierto")).toBeInTheDocument();
    expect(
      JSON.parse(screen.getByTestId("location").textContent).state
    ).toEqual({ studentListLocation: "/app/alumnos" });
  });
});
