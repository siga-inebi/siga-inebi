import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { AlumnosPage } from "@students/AlumnosPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const studentsServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
}));

vi.mock("@students/studentsService.js", () => ({
  studentsService: studentsServiceMock,
}));

const downloadCsvMock = vi.hoisted(() => vi.fn());

vi.mock("@shared/utils/csv.js", () => ({ downloadCsv: downloadCsvMock }));

const SAMPLE = [
  {
    id: 1,
    person: {
      id: 11,
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
    person: {
      id: 12,
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
    expect(
      screen.getByText(/Mostrando 1–2 de 2/)
    ).toBeInTheDocument();
  });

  test("shows an empty state when the search does not match", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.type(
      screen.getByPlaceholderText("Buscar por nombre…"),
      "Nadie"
    );

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

  test("opens the detail panel for a row", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);

    expect(
      screen.getByRole("heading", { name: "Maria Jose Lopez Garcia" })
    ).toBeInTheDocument();
    expect(screen.getByText("maria@example.test")).toBeInTheDocument();
  });

  test("opens and closes the photo lightbox from the detail panel", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);

    expect(
      screen.queryByRole("dialog", { name: "Foto de Maria Jose Lopez Garcia" })
    ).not.toBeInTheDocument();

    const detailWindow = screen.getByRole("dialog", {
      name: "Maria Jose Lopez Garcia",
    });
    await user.click(
      within(detailWindow).getByAltText("Foto de Maria Jose Lopez Garcia")
    );

    const lightbox = screen.getByRole("dialog", {
      name: "Foto de Maria Jose Lopez Garcia",
    });
    const downloadLink = within(lightbox).getByRole("link", {
      name: "Descargar",
    });
    expect(downloadLink).toHaveAttribute(
      "href",
      "http://localhost/media/student_photos/maria.png"
    );
    expect(downloadLink).toHaveAttribute("download", "maria.png");

    await user.click(
      within(lightbox).getByRole("button", { name: "Cerrar imagen" })
    );
    // El dialogo se desmonta al terminar su animacion de salida, no en el clic.
    await waitFor(() =>
      expect(
        screen.queryByRole("dialog", { name: "Foto de Maria Jose Lopez Garcia" })
      ).not.toBeInTheDocument()
    );
  });

  test("submits the create form against the mock service", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    studentsServiceMock.create.mockResolvedValue({
      id: 3,
      person: {
        id: 13,
        first_name: "Nueva",
        last_name: "Alumna",
        email: "",
        phone_number: "",
      },
      student_code: "EST-2026-099",
      status: "pre_enrolled",
      photo: "",
    });
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getByRole("button", { name: /Nuevo estudiante/ }));

    await user.type(screen.getByLabelText(/^Nombres/), "Nueva");
    await user.type(screen.getByLabelText(/^Apellidos/), "Alumna");
    await user.type(screen.getByLabelText(/^Correo/), "nueva@example.test");
    await user.type(screen.getByLabelText(/^Telefono/), "555-0199");
    await user.type(
      screen.getByLabelText(/^Codigo de estudiante/),
      "EST-2026-099"
    );
    await user.click(screen.getByRole("button", { name: /Crear estudiante/ }));

    await waitFor(() =>
      expect(studentsServiceMock.create).toHaveBeenCalledTimes(1)
    );
    expect(studentsServiceMock.create).toHaveBeenCalledWith(
      expect.objectContaining({
        person: {
          first_name: "Nueva",
          last_name: "Alumna",
          email: "nueva@example.test",
          phone_number: "555-0199",
        },
        student_code: "EST-2026-099",
        status: "pre_enrolled",
      })
    );
    expect(await screen.findByText("Nueva Alumna")).toBeInTheDocument();
  });

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

  test("edits a student via the detail panel", async () => {
    studentsServiceMock.list.mockResolvedValue(SAMPLE);
    studentsServiceMock.update.mockResolvedValue({
      id: 1,
      person: {
        id: 11,
        first_name: "Maria Jose",
        last_name: "Lopez Mendez",
        email: "maria@example.test",
        phone_number: "555-0101",
      },
      student_code: "EST-2026-014",
      status: "active",
      photo: "",
    });
    const user = userEvent.setup();
    renderWithRouter(<AlumnosPage />);

    await screen.findByText("Maria Jose Lopez Garcia");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);
    await user.click(screen.getByRole("button", { name: "Editar" }));

    const lastNameInput = screen.getByLabelText(/^Apellidos/);
    expect(lastNameInput).toHaveValue("Lopez Garcia");
    await user.clear(lastNameInput);
    await user.type(lastNameInput, "Lopez Mendez");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() =>
      expect(studentsServiceMock.update).toHaveBeenCalledTimes(1)
    );
    expect(studentsServiceMock.update).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        person: {
          id: 11,
          first_name: "Maria Jose",
          last_name: "Lopez Mendez",
          email: "maria@example.test",
          phone_number: "555-0101",
        },
        student_code: "EST-2026-014",
      })
    );
    expect(
      await screen.findByRole("heading", { name: "Maria Jose Lopez Mendez" })
    ).toBeInTheDocument();
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
});
