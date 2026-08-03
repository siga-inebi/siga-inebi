import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { AlumnosPage } from "../pages/AlumnosPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const studentsServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  create: vi.fn(),
}));

vi.mock("../services/studentsService.js", () => ({
  studentsService: studentsServiceMock,
}));

const downloadCsvMock = vi.hoisted(() => vi.fn());

vi.mock("../utils/csv.js", () => ({ downloadCsv: downloadCsvMock }));

const SAMPLE = [
  {
    id: 1,
    first_name: "Maria Jose",
    last_name: "Lopez Garcia",
    gender: "Femenino",
    student_code: "EST-2026-014",
    status: "active",
    section: { grade: "3ro", name: "A" },
    birth_date: "2010-03-14",
    cui: "2451 23456 0101",
    age: 16,
    clave: "01",
  },
  {
    id: 2,
    first_name: "Carlos Enrique",
    last_name: "Ramirez Perez",
    gender: "Masculino",
    student_code: "EST-2026-015",
    status: "active",
    section: { grade: "2do", name: "B" },
    birth_date: "2011-06-02",
    cui: "2451 23457 0102",
    age: 15,
    clave: "02",
  },
];

describe("AlumnosPage", () => {
  beforeEach(() => {
    studentsServiceMock.list.mockReset();
    studentsServiceMock.create.mockReset();
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
      within(screen.getByRole("table")).getByText('3ro "A"')
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Mostrando 1-2 de 2 registros/)
    ).toBeInTheDocument();
  });

  test("shows an empty state when the search does not match", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.type(
      screen.getByPlaceholderText("Buscar por nombre..."),
      "Nadie"
    );

    expect(
      screen.getByText("No hay alumnos que coincidan con la busqueda.")
    ).toBeInTheDocument();
  });

  test("filters by seccion", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.selectOptions(screen.getByLabelText("Filtrar"), '2do "B"');

    expect(
      screen.queryByText("Maria Jose Lopez Garcia")
    ).not.toBeInTheDocument();
    expect(screen.getByText("Carlos Enrique Ramirez Perez")).toBeInTheDocument();
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

  test("opens the detail panel for a row", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getAllByRole("button", { name: "Ver detalle" })[0]);

    expect(
      screen.getByRole("heading", { name: "Maria Jose Lopez Garcia" })
    ).toBeInTheDocument();
    expect(screen.getByText("2451 23456 0101")).toBeInTheDocument();
  });

  test("submits the create form against the mock service", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    studentsServiceMock.create.mockResolvedValue({
      id: 3,
      first_name: "Nueva",
      last_name: "Alumna",
      gender: "Femenino",
      student_code: "EST-2026-099",
      status: "pre_enrolled",
      section: null,
    });
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: "+ Agregar nuevo" }));

    await user.type(screen.getByLabelText("Nombres"), "Nueva");
    await user.type(screen.getByLabelText("Apellidos"), "Alumna");
    await user.selectOptions(screen.getByLabelText("Genero"), "Femenino");
    await user.type(
      screen.getByLabelText("Codigo de estudiante"),
      "EST-2026-099"
    );
    await user.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() =>
      expect(studentsServiceMock.create).toHaveBeenCalledTimes(1)
    );
    expect(studentsServiceMock.create).toHaveBeenCalledWith(
      expect.objectContaining({
        first_name: "Nueva",
        last_name: "Alumna",
        gender: "Femenino",
        student_code: "EST-2026-099",
        status: "pre_enrolled",
        section: null,
      })
    );
    expect(await screen.findByText("Nueva Alumna")).toBeInTheDocument();
  });

  test("requires the mandatory fields before submitting", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: "+ Agregar nuevo" }));
    await user.click(screen.getByRole("button", { name: "Guardar" }));

    expect(screen.getByText(/es obligatorio/)).toBeInTheDocument();
    expect(studentsServiceMock.create).not.toHaveBeenCalled();
  });
});
