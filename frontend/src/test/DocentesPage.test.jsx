import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { DocentesPage } from "../pages/DocentesPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const teachersServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  create: vi.fn(),
}));

vi.mock("../services/teachersService.js", () => ({
  teachersService: teachersServiceMock,
}));

const downloadCsvMock = vi.hoisted(() => vi.fn());

vi.mock("../utils/csv.js", () => ({ downloadCsv: downloadCsvMock }));

const SAMPLE = [
  {
    id: 1,
    first_name: "Prof. Marvin Estuardo",
    last_name: "Lopez Cifuentes",
    specialty: "Electricidad Industrial",
    position: "Docente Titulado",
    employee_code: "EMP-0142",
    phone_number: "5566-1234",
    appointment_date: "2019-01-15",
  },
  {
    id: 2,
    first_name: "Licda. Karen Yesenia",
    last_name: "Vasquez Us",
    specialty: "Orientacion Educativa",
    position: "Orientador/a",
    employee_code: "EMP-0176",
    phone_number: "5588-4433",
    appointment_date: "2021-07-05",
  },
];

describe("DocentesPage", () => {
  beforeEach(() => {
    teachersServiceMock.list.mockReset();
    teachersServiceMock.create.mockReset();
    downloadCsvMock.mockReset();
  });

  test("exports the currently filtered rows as CSV", async () => {
    teachersServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Prof. Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getByRole("button", { name: "Exportar CSV" }));

    expect(downloadCsvMock).toHaveBeenCalledTimes(1);
    const [filename, , rows] = downloadCsvMock.mock.calls[0];
    expect(filename).toBe("docentes.csv");
    expect(rows).toEqual(SAMPLE);
  });

  test("renders the list once loaded", async () => {
    teachersServiceMock.list.mockResolvedValue(SAMPLE);
    renderWithRouter(<DocentesPage />);

    expect(
      await screen.findByText("Prof. Marvin Estuardo Lopez Cifuentes")
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("table")).getByText("EMP-0142")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Mostrando 1-2 de 2 registros/)
    ).toBeInTheDocument();
  });

  test("shows an empty state when the search does not match", async () => {
    teachersServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Prof. Marvin Estuardo Lopez Cifuentes");
    await user.type(
      screen.getByPlaceholderText("Buscar por nombre..."),
      "Nadie"
    );

    expect(
      screen.getByText("No hay docentes que coincidan con la busqueda.")
    ).toBeInTheDocument();
  });

  test("filters by puesto", async () => {
    teachersServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Prof. Marvin Estuardo Lopez Cifuentes");
    await user.selectOptions(screen.getByLabelText("Filtrar"), "Orientador/a");

    expect(
      screen.queryByText("Prof. Marvin Estuardo Lopez Cifuentes")
    ).not.toBeInTheDocument();
    expect(
      screen.getByText("Licda. Karen Yesenia Vasquez Us")
    ).toBeInTheDocument();
  });

  test("shows the service error instead of the table", async () => {
    teachersServiceMock.list.mockRejectedValue(
      new Error("Solicitud no completada.")
    );
    renderWithRouter(<DocentesPage />);

    expect(
      await screen.findByText("Solicitud no completada.")
    ).toBeInTheDocument();
  });

  test("opens the detail panel for a row", async () => {
    teachersServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Prof. Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getAllByRole("button", { name: "Ver detalle" })[0]);

    expect(
      screen.getByRole("heading", {
        name: "Prof. Marvin Estuardo Lopez Cifuentes",
      })
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("complementary")).getByText(
        "Electricidad Industrial"
      )
    ).toBeInTheDocument();
  });

  test("submits the create form (single nombres completos field) against the mock service", async () => {
    teachersServiceMock.list.mockResolvedValue(SAMPLE);
    teachersServiceMock.create.mockResolvedValue({
      id: 3,
      first_name: "Prof. Nueva Docente",
      last_name: "",
      specialty: "Fisica",
      position: "Docente Interino",
      employee_code: "EMP-0300",
      phone_number: "5511-2233",
    });
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Prof. Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getByRole("button", { name: "+ Agregar nuevo" }));

    await user.type(
      screen.getByLabelText("Nombres completos"),
      "Prof. Nueva Docente"
    );
    await user.type(screen.getByLabelText("Especialidad"), "Fisica");
    await user.selectOptions(
      screen.getByLabelText("Puesto"),
      "Docente Interino"
    );
    await user.type(screen.getByLabelText("Codigo de Empleado"), "EMP-0300");
    await user.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() =>
      expect(teachersServiceMock.create).toHaveBeenCalledTimes(1)
    );
    expect(teachersServiceMock.create).toHaveBeenCalledWith(
      expect.objectContaining({
        first_name: "Prof. Nueva Docente",
        last_name: "",
        specialty: "Fisica",
        position: "Docente Interino",
        employee_code: "EMP-0300",
      })
    );
    expect(
      await screen.findByText("Prof. Nueva Docente")
    ).toBeInTheDocument();
  });

  test("requires the mandatory fields before submitting", async () => {
    teachersServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Prof. Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getByRole("button", { name: "+ Agregar nuevo" }));
    await user.click(screen.getByRole("button", { name: "Guardar" }));

    expect(screen.getByText(/es obligatorio/)).toBeInTheDocument();
    expect(teachersServiceMock.create).not.toHaveBeenCalled();
  });
});
