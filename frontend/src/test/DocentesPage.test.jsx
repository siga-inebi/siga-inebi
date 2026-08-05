import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { DocentesPage } from "../pages/DocentesPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const teachersServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
}));

vi.mock("../services/teachersService.js", () => ({
  teachersService: teachersServiceMock,
}));

const downloadCsvMock = vi.hoisted(() => vi.fn());

vi.mock("../utils/csv.js", () => ({ downloadCsv: downloadCsvMock }));

const SAMPLE = [
  {
    id: 1,
    person: {
      id: 21,
      first_name: "Marvin Estuardo",
      last_name: "Lopez Cifuentes",
      email: "marvin@example.test",
      phone_number: "5566-1234",
    },
    specialty: "Electricidad Industrial",
    position: "Docente Titulado",
    employee_code: "EMP-0142",
    appointment_date: "2019-01-15",
    photo: "http://localhost/media/teacher_photos/marvin.png",
  },
  {
    id: 2,
    person: {
      id: 22,
      first_name: "Karen Yesenia",
      last_name: "Vasquez Us",
      email: "karen@example.test",
      phone_number: "5588-4433",
    },
    specialty: "Orientacion Educativa",
    position: "Orientador/a",
    employee_code: "EMP-0176",
    appointment_date: "2021-07-05",
    photo: "",
  },
];

describe("DocentesPage", () => {
  beforeEach(() => {
    teachersServiceMock.list.mockReset();
    teachersServiceMock.create.mockReset();
    teachersServiceMock.update.mockReset();
    downloadCsvMock.mockReset();
  });

  test("exports the currently filtered rows as CSV", async () => {
    teachersServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
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
      await screen.findByText("Marvin Estuardo Lopez Cifuentes")
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

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
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

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.selectOptions(screen.getByLabelText("Filtrar"), "Orientador/a");

    expect(
      screen.queryByText("Marvin Estuardo Lopez Cifuentes")
    ).not.toBeInTheDocument();
    expect(screen.getByText("Karen Yesenia Vasquez Us")).toBeInTheDocument();
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

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getAllByRole("button", { name: "Ver detalle" })[0]);

    expect(
      screen.getByRole("heading", { name: "Marvin Estuardo Lopez Cifuentes" })
    ).toBeInTheDocument();
    expect(screen.getByText("marvin@example.test")).toBeInTheDocument();
  });

  test("opens and closes the photo lightbox from the detail panel", async () => {
    teachersServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getAllByRole("button", { name: "Ver detalle" })[0]);

    const detailPanel = screen.getByRole("complementary", {
      name: "Detalle de Marvin Estuardo Lopez Cifuentes",
    });
    await user.click(within(detailPanel).getByRole("button", { name: "" }));

    const lightbox = screen.getByRole("dialog", {
      name: "Marvin Estuardo Lopez Cifuentes",
    });
    expect(lightbox).toBeInTheDocument();
    const downloadLink = within(lightbox).getByRole("link", {
      name: "Descargar",
    });
    expect(downloadLink).toHaveAttribute(
      "href",
      "http://localhost/media/teacher_photos/marvin.png"
    );
    expect(downloadLink).toHaveAttribute("download", "marvin.png");

    await user.click(
      within(lightbox).getByRole("button", { name: "Cerrar imagen" })
    );
    expect(
      screen.queryByRole("dialog", { name: "Marvin Estuardo Lopez Cifuentes" })
    ).not.toBeInTheDocument();
  });

  test("submits the create form against the mock service", async () => {
    teachersServiceMock.list.mockResolvedValue(SAMPLE);
    teachersServiceMock.create.mockResolvedValue({
      id: 3,
      person: {
        id: 23,
        first_name: "Nueva",
        last_name: "Docente",
        email: "",
        phone_number: "",
      },
      specialty: "Fisica",
      position: "Docente Interino",
      employee_code: "EMP-0300",
      appointment_date: null,
      photo: "",
    });
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getByRole("button", { name: "+ Agregar nuevo" }));

    await user.type(screen.getByLabelText("Nombres"), "Nueva");
    await user.type(screen.getByLabelText("Apellidos"), "Docente");
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
        person: {
          first_name: "Nueva",
          last_name: "Docente",
          email: "",
          phone_number: "",
        },
        specialty: "Fisica",
        position: "Docente Interino",
        employee_code: "EMP-0300",
      })
    );
    expect(await screen.findByText("Nueva Docente")).toBeInTheDocument();
  });

  test("previews a newly selected photo in the create form", async () => {
    teachersServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getByRole("button", { name: "+ Agregar nuevo" }));

    expect(screen.queryByAltText("Vista previa")).not.toBeInTheDocument();

    const file = new File(["fake-image-bytes"], "avatar.png", {
      type: "image/png",
    });
    await user.upload(screen.getByLabelText("Foto"), file);

    expect(await screen.findByAltText("Vista previa")).toHaveAttribute(
      "src",
      "blob:mock-url"
    );
  });

  test("edits a teacher via the detail panel", async () => {
    teachersServiceMock.list.mockResolvedValue(SAMPLE);
    teachersServiceMock.update.mockResolvedValue({
      id: 1,
      person: {
        id: 21,
        first_name: "Marvin Estuardo",
        last_name: "Lopez Mendez",
        email: "marvin@example.test",
        phone_number: "5566-1234",
      },
      specialty: "Electricidad Industrial",
      position: "Docente Titulado",
      employee_code: "EMP-0142",
      appointment_date: "2019-01-15",
      photo: "",
    });
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getAllByRole("button", { name: "Ver detalle" })[0]);
    await user.click(screen.getByRole("button", { name: "Editar" }));

    const lastNameInput = screen.getByLabelText("Apellidos");
    expect(lastNameInput).toHaveValue("Lopez Cifuentes");
    await user.clear(lastNameInput);
    await user.type(lastNameInput, "Lopez Mendez");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() =>
      expect(teachersServiceMock.update).toHaveBeenCalledTimes(1)
    );
    expect(teachersServiceMock.update).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        person: {
          id: 21,
          first_name: "Marvin Estuardo",
          last_name: "Lopez Mendez",
          email: "marvin@example.test",
          phone_number: "5566-1234",
        },
        specialty: "Electricidad Industrial",
        position: "Docente Titulado",
        employee_code: "EMP-0142",
      })
    );
    expect(
      await screen.findByRole("heading", {
        name: "Marvin Estuardo Lopez Mendez",
      })
    ).toBeInTheDocument();
  });

  test("requires the mandatory fields before submitting", async () => {
    teachersServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getByRole("button", { name: "+ Agregar nuevo" }));
    await user.click(screen.getByRole("button", { name: "Guardar" }));

    expect(screen.getByText(/es obligatorio/)).toBeInTheDocument();
    expect(teachersServiceMock.create).not.toHaveBeenCalled();
  });
});
