import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { DocentesPage } from "@teachers/DocentesPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import { selectOption } from "./helpers/selectOption.jsx";
import {
  editInstitutionalPerson,
  editedInstitutionalPerson,
  fillInstitutionalPerson,
  institutionalPerson,
  visibleInstitutionalPerson,
} from "./helpers/institutionalPerson.js";

const teachersServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
  listPage: vi.fn(),
  get: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  // El alta pide el codigo sugerido al abrir el formulario. Sin el doble, la
  // pantalla caia en el catch de `suggestedOrBlank` y la prueba pasaba por el
  // camino de error en vez del real.
  nextCode: vi.fn(),
}));

vi.mock("@teachers/teachersService.js", () => ({
  teachersService: teachersServiceMock,
}));

const downloadCsvMock = vi.hoisted(() => vi.fn());

vi.mock("@shared/utils/csv.js", () => ({ downloadCsv: downloadCsvMock }));

/** Sobre paginado de DRF: la pantalla solo pide la pagina visible. */
const page = (rows, count = rows.length) => ({
  count,
  next: null,
  previous: null,
  results: rows,
});

const SAMPLE = [
  {
    id: 1,
    person: {
      ...visibleInstitutionalPerson,
      public_id: "person-21",
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
      public_id: "person-22",
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
    teachersServiceMock.listPage.mockReset();
    teachersServiceMock.create.mockReset();
    teachersServiceMock.update.mockReset();
    downloadCsvMock.mockReset();
  });

  test("exports every page of the current search and puesto as CSV", async () => {
    teachersServiceMock.listPage.mockResolvedValue(page(SAMPLE));
    teachersServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />, {
      route: "/?search=Lopez&position=Docente+Titulado",
    });

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getByRole("button", { name: "Exportar CSV" }));

    await waitFor(() => expect(downloadCsvMock).toHaveBeenCalledTimes(1));
    expect(teachersServiceMock.list).toHaveBeenCalledWith({
      search: "Lopez",
      position: "Docente Titulado",
    });
    const [filename, , rows] = downloadCsvMock.mock.calls[0];
    expect(filename).toBe("docentes.csv");
    expect(rows).toEqual(SAMPLE);
  });

  test("asks the server only for the visible page and shows its total", async () => {
    teachersServiceMock.listPage.mockResolvedValue(page(SAMPLE, 100));
    renderWithRouter(<DocentesPage />);

    expect(
      await screen.findByText("Marvin Estuardo Lopez Cifuentes")
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("table")).getByText("EMP-0142")
    ).toBeInTheDocument();
    expect(teachersServiceMock.listPage).toHaveBeenCalledTimes(1);
    expect(teachersServiceMock.listPage).toHaveBeenCalledWith({
      page: 1,
      page_size: 25,
    });
    expect(teachersServiceMock.list).not.toHaveBeenCalled();
    expect(
      screen.getByText("100 registros de personal docente y administrativo.")
    ).toBeInTheDocument();
  });

  test("sends the search to the server and shows its empty state", async () => {
    teachersServiceMock.listPage.mockImplementation(async (params) =>
      params.search ? page([]) : page(SAMPLE)
    );
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.type(
      screen.getByPlaceholderText("Buscar por nombre, codigo o CUI…"),
      "Nadie"
    );

    expect(
      await screen.findByText("Sin datos para los filtros seleccionados.")
    ).toBeInTheDocument();
    expect(teachersServiceMock.listPage).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 25,
      search: "Nadie",
    });
  });

  test("sends the puesto filter to the server and clears it", async () => {
    teachersServiceMock.listPage.mockImplementation(async (params) =>
      page(
        params.position
          ? SAMPLE.filter((teacher) => teacher.position === params.position)
          : SAMPLE
      )
    );
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await selectOption(user, /^Filtrar por puesto/, "Orientador/a");

    await waitFor(() =>
      expect(
        screen.queryByText("Marvin Estuardo Lopez Cifuentes")
      ).not.toBeInTheDocument()
    );
    expect(screen.getByText("Karen Yesenia Vasquez Us")).toBeInTheDocument();
    expect(teachersServiceMock.listPage).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 25,
      position: "Orientador/a",
    });

    await user.click(screen.getByRole("button", { name: /Limpiar/ }));

    expect(
      await screen.findByText("Marvin Estuardo Lopez Cifuentes")
    ).toBeInTheDocument();
    // La pagina sin filtro sale de la cache de la primera carga; lo que importa
    // es que el puesto dejo de viajar y que no queda nada por limpiar.
    expect(
      screen.queryByRole("button", { name: /Limpiar/ })
    ).not.toBeInTheDocument();
  });

  test("shows the service error instead of the table", async () => {
    teachersServiceMock.listPage.mockRejectedValue(
      new Error("Solicitud no completada.")
    );
    renderWithRouter(<DocentesPage />);

    expect(
      await screen.findByText("Solicitud no completada.")
    ).toBeInTheDocument();
  });

  test("opens the detail panel for a row", async () => {
    teachersServiceMock.listPage.mockResolvedValue(page(SAMPLE));
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);

    expect(
      screen.getByRole("heading", { name: "Marvin Estuardo Lopez Cifuentes" })
    ).toBeInTheDocument();
    expect(screen.getByText("marvin@example.test")).toBeInTheDocument();
  });

  test("opens and closes the photo lightbox from the detail panel", async () => {
    teachersServiceMock.listPage.mockResolvedValue(page(SAMPLE));
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);

    const detailWindow = screen.getByRole("dialog", {
      name: "Marvin Estuardo Lopez Cifuentes",
    });
    await user.click(
      within(detailWindow).getByAltText(
        "Foto de Marvin Estuardo Lopez Cifuentes"
      )
    );

    const lightbox = screen.getByRole("dialog", {
      name: "Foto de Marvin Estuardo Lopez Cifuentes",
    });
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
    // El dialogo se desmonta al terminar su animacion de salida, no en el clic.
    await waitFor(() =>
      expect(
        screen.queryByRole("dialog", {
          name: "Foto de Marvin Estuardo Lopez Cifuentes",
        })
      ).not.toBeInTheDocument()
    );
  });

  test("submits the create form against the mock service", async () => {
    const createdTeacher = {
      id: 3,
      person: {
        public_id: "person-23",
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
    };
    teachersServiceMock.listPage
      .mockResolvedValueOnce(page(SAMPLE))
      .mockResolvedValueOnce(page([...SAMPLE, createdTeacher]));
    teachersServiceMock.nextCode.mockResolvedValue("DOC-013");
    teachersServiceMock.create.mockResolvedValue(createdTeacher);
    // Sin pausa entre pulsaciones: lo que se prueba es el envío del formulario,
    // no el tecleo, y con pausa son más de treinta vueltas del bucle de eventos.
    const user = userEvent.setup({ delay: null });
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getByRole("button", { name: /Nuevo registro/ }));

    await user.type(screen.getByLabelText(/^Nombres/), "Nueva");
    await user.type(screen.getByLabelText(/^Apellidos/), "Docente");
    await fillInstitutionalPerson(user);
    await user.type(screen.getByLabelText(/^Especialidad/), "Fisica");
    await selectOption(user, /^Puesto/, "Docente Interino");
    const codeField = screen.getByLabelText(/^Código de empleado/i);
    // Llega prellenado con la sugerencia del backend, y se puede sobreescribir.
    expect(codeField).toHaveValue("DOC-013");
    await user.clear(codeField);
    await user.type(codeField, "EMP-0300");
    await user.click(screen.getByRole("button", { name: /Crear registro/ }));

    await waitFor(() =>
      expect(teachersServiceMock.create).toHaveBeenCalledTimes(1)
    );
    expect(teachersServiceMock.create).toHaveBeenCalledWith(
      expect.objectContaining({
        person: {
          ...institutionalPerson,
          first_name: "Nueva",
          last_name: "Docente",
        },
        specialty: "Fisica",
        position: "Docente Interino",
        employee_code: "EMP-0300",
      })
    );
    await waitFor(() =>
      expect(teachersServiceMock.listPage).toHaveBeenCalledTimes(2)
    );
    expect(await screen.findByText("Nueva Docente")).toBeInTheDocument();
    // 30 s y no los 15 globales: con la suite completa en paralelo el tecleo
    // del formulario ya rondaba los 14 s, y la recarga posterior al alta
    // dejaba la prueba al borde del limite.
  }, 30000);

  test("previews a newly selected photo in the create form", async () => {
    teachersServiceMock.listPage.mockResolvedValue(page(SAMPLE));
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getByRole("button", { name: /Nuevo registro/ }));

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

  test("edits a teacher via the detail panel", async () => {
    teachersServiceMock.listPage.mockResolvedValue(page(SAMPLE));
    teachersServiceMock.update.mockResolvedValue({
      id: 1,
      person: {
        ...visibleInstitutionalPerson,
        ...editedInstitutionalPerson,
        public_id: "person-21",
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
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);
    await user.click(screen.getByRole("button", { name: "Editar" }));

    const lastNameInput = screen.getByLabelText(/^Apellidos/);
    expect(lastNameInput).toHaveValue("Lopez Cifuentes");
    await user.clear(lastNameInput);
    await user.type(lastNameInput, "Lopez Mendez");
    expect(screen.queryByLabelText(/^CUI/)).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText(/^Fecha de nacimiento/)
    ).not.toBeInTheDocument();
    await editInstitutionalPerson(user);
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() =>
      expect(teachersServiceMock.update).toHaveBeenCalledTimes(1)
    );
    expect(teachersServiceMock.update).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        person: {
          ...visibleInstitutionalPerson,
          ...editedInstitutionalPerson,
          public_id: "person-21",
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
  }, 15000);

  test("requires the mandatory fields before submitting", async () => {
    teachersServiceMock.listPage.mockResolvedValue(page(SAMPLE));
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getByRole("button", { name: /Nuevo registro/ }));
    await user.click(screen.getByRole("button", { name: /Crear registro/ }));

    expect(screen.getByText(/Complete el campo/)).toBeInTheDocument();
    expect(teachersServiceMock.create).not.toHaveBeenCalled();
  });
});
