import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { useLocation } from "react-router-dom";

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
  listPositions: vi.fn(),
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

const documentsServiceMock = vi.hoisted(() => ({
  listTeacherRecords: vi.fn(),
}));
vi.mock("@documents/documentsService.js", () => ({
  documentsService: documentsServiceMock,
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
const POSITIONS = [
  "Docente Titulado",
  "Docente Interino",
  "Orientador/a",
  "Administrativo",
].map((value) => ({ value, label: value }));
function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.search}</output>;
}

const SAMPLE = [
  {
    id: 1,
    public_id: "teacher-1",
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
    public_id: "teacher-2",
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
    teachersServiceMock.listPage.mockReset().mockResolvedValue(paged(SAMPLE));
    teachersServiceMock.listPositions.mockReset().mockResolvedValue(POSITIONS);
    teachersServiceMock.create.mockReset();
    teachersServiceMock.update.mockReset();
    downloadCsvMock.mockReset();
    documentsServiceMock.listTeacherRecords
      .mockReset()
      .mockResolvedValue(paged([]));
  });

  test("renders the list once loaded", async () => {
    teachersServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
    renderWithRouter(<DocentesPage />);

    expect(
      await screen.findByText("Marvin Estuardo Lopez Cifuentes")
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("table")).getByText("EMP-0142")
    ).toBeInTheDocument();
    expect(screen.getByText(/Mostrando 1–2 de 2/)).toBeInTheDocument();
  });

  test("recupera filtros, actividad y página desde URL sin descargar todo el padrón", async () => {
    teachersServiceMock.listPage.mockResolvedValue(paged(SAMPLE, 2500));
    renderWithRouter(<DocentesPage />, {
      route:
        "/app/docentes?page=2&page_size=50&search=EMP&position=Orientador%2Fa&include_inactive=1",
    });
    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    expect(teachersServiceMock.listPage).toHaveBeenCalledExactlyOnceWith({
      page: 2,
      page_size: 50,
      search: "EMP",
      position: "Orientador/a",
      include_inactive: true,
    });
    expect(teachersServiceMock.listPositions).toHaveBeenCalledTimes(1);
    expect(teachersServiceMock.list).not.toHaveBeenCalled();
    expect(screen.getByText(/2500 registros de personal/)).toBeInTheDocument();
    expect(
      screen.getByRole("switch", { name: "Mostrar desactivados" })
    ).toBeChecked();
  });

  test("pagina, cambia tamaño y limpia filtros conservando la búsqueda del servidor", async () => {
    teachersServiceMock.listPage.mockResolvedValue(paged(SAMPLE, 2500));
    const user = userEvent.setup();
    renderWithRouter(
      <>
        <DocentesPage />
        <LocationProbe />
      </>,
      { route: "/app/docentes?position=Orientador%2Fa&include_inactive=1" }
    );
    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await waitFor(() =>
      expect(teachersServiceMock.listPage).toHaveBeenLastCalledWith({
        page: 2,
        page_size: 25,
        position: "Orientador/a",
        include_inactive: true,
      })
    );
    await selectOption(user, /Filas por página/, "50");
    await waitFor(() =>
      expect(teachersServiceMock.listPage).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 50,
        position: "Orientador/a",
        include_inactive: true,
      })
    );
    await user.type(
      screen.getByPlaceholderText(/Buscar por nombre/),
      "EMP-0142"
    );
    expect(screen.getByRole("button", { name: "Exportar CSV" })).toBeDisabled();
    await waitFor(() =>
      expect(teachersServiceMock.listPage).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 50,
        position: "Orientador/a",
        include_inactive: true,
        search: "EMP-0142",
      })
    );
    expect(screen.getByPlaceholderText(/Buscar por nombre/)).toHaveValue(
      "EMP-0142"
    );
    await user.click(
      screen.getByRole("button", { name: "Limpiar", exact: true })
    );
    await waitFor(() =>
      expect(teachersServiceMock.listPage).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 50,
      })
    );
    expect(screen.getByTestId("location")).toHaveTextContent("?page_size=50");
    expect(teachersServiceMock.list).not.toHaveBeenCalled();
  });

  test("exporta más de mil filas con los filtros de servidor desde la primera página", async () => {
    const rows = Array.from({ length: 1001 }, (_, index) => ({
      ...SAMPLE[0],
      id: index + 1,
      employee_code: `DOC-DEMO-${index + 1}`,
    }));
    teachersServiceMock.listPage.mockImplementation(
      async ({ page, page_size }) =>
        paged(
          rows.slice((page - 1) * page_size, page * page_size),
          rows.length,
          page * page_size < rows.length ? "next" : null
        )
    );
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />, {
      route:
        "/app/docentes?page=2&search=DOC-DEMO&position=Docente+Titulado&include_inactive=1",
    });
    await screen.findByText("DOC-DEMO-26");
    expect(teachersServiceMock.listPage).toHaveBeenCalledTimes(1);
    expect(downloadCsvMock).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Exportar CSV" }));
    await waitFor(() => expect(downloadCsvMock).toHaveBeenCalledTimes(1));
    const [filename, csv] = downloadCsvMock.mock.calls[0];
    expect(filename).toBe("docentes.csv");
    expect(csv).toContain("DOC-DEMO-1001");
    expect(csv.trim().split(/\r?\n/)).toHaveLength(1002);
    const calls = teachersServiceMock.listPage.mock.calls.slice(1);
    expect(calls).toHaveLength(11);
    calls.forEach(([params], index) =>
      expect(params).toEqual({
        search: "DOC-DEMO",
        position: "Docente Titulado",
        include_inactive: true,
        page: index + 1,
        page_size: 100,
      })
    );
  });

  test("un catálogo fallido permite seguir consultando y reintentar sin inventar puestos", async () => {
    teachersServiceMock.listPositions.mockRejectedValue(
      new Error("Catálogo no disponible")
    );
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);
    await screen.findByText(/No se pudo cargar el catálogo de puestos/);
    expect(
      screen.getByText("Marvin Estuardo Lopez Cifuentes")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Nuevo registro/ })
    ).toBeDisabled();
    teachersServiceMock.listPositions.mockResolvedValue([
      { value: "puesto-servidor", label: "Puesto del servidor" },
    ]);
    await user.click(
      screen.getByRole("button", { name: "Reintentar puestos" })
    );
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /Nuevo registro/ })
      ).toBeEnabled()
    );
    await user.click(screen.getByRole("button", { name: /Nuevo registro/ }));
    await selectOption(user, /^Puesto/, "Puesto del servidor");
    expect(screen.getByRole("combobox", { name: /^Puesto/ })).toHaveTextContent(
      "Puesto del servidor"
    );
  });

  test("shows an empty state when the search does not match", async () => {
    teachersServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    teachersServiceMock.listPage.mockResolvedValue(paged([]));
    await user.type(screen.getByPlaceholderText(/Buscar por nombre/), "Nadie");

    expect(
      await screen.findByText("Sin datos para los filtros seleccionados.")
    ).toBeInTheDocument();
  });

  test("filters by puesto", async () => {
    teachersServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    teachersServiceMock.listPage.mockResolvedValue(paged([SAMPLE[1]]));
    await selectOption(user, /^Filtrar por puesto/, "Orientador/a");
    await waitFor(() =>
      expect(teachersServiceMock.listPage).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 25,
        position: "Orientador/a",
      })
    );
    await screen.findByText("Karen Yesenia Vasquez Us");

    expect(
      screen.queryByText("Marvin Estuardo Lopez Cifuentes")
    ).not.toBeInTheDocument();
    expect(screen.getByText("Karen Yesenia Vasquez Us")).toBeInTheDocument();
  });

  test("shows the service error instead of the table", async () => {
    teachersServiceMock.listPage.mockRejectedValue(
      new Error("Solicitud no completada.")
    );
    renderWithRouter(<DocentesPage />);

    expect(
      await screen.findByText("Solicitud no completada.")
    ).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    teachersServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Reintentar listado" }));
    expect(
      await screen.findByText("Marvin Estuardo Lopez Cifuentes")
    ).toBeInTheDocument();
  });

  test("opens the detail panel for a row", async () => {
    teachersServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);

    expect(
      screen.getByRole("heading", { name: "Marvin Estuardo Lopez Cifuentes" })
    ).toBeInTheDocument();
    expect(screen.getByText("marvin@example.test")).toBeInTheDocument();
  });

  test("el detalle alterna pantalla completa y reaparece en tamano normal", async () => {
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);

    await user.click(screen.getByRole("button", { name: "Pantalla completa" }));
    expect(
      screen.getByRole("button", { name: "Salir de pantalla completa" })
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Salir de pantalla completa" })
    );
    expect(
      screen.getByRole("button", { name: "Pantalla completa" })
    ).toBeInTheDocument();

    // Al cerrar y abrir otro registro, la ventana vuelve a su tamano normal.
    // Se espera el desmontaje real: durante la animacion de salida el titulo ya
    // queda vacio pero el dialogo sigue ocultando el listado con aria-hidden.
    await user.click(screen.getByRole("button", { name: "Cerrar" }));
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    );
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[1]);
    expect(
      screen.getByRole("button", { name: "Pantalla completa" })
    ).toBeInTheDocument();
  });

  test("carga el expediente documental únicamente al solicitarlo", async () => {
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);
    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    expect(documentsServiceMock.listTeacherRecords).not.toHaveBeenCalled();
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);
    expect(documentsServiceMock.listTeacherRecords).not.toHaveBeenCalled();
    await user.click(
      screen.getByRole("button", { name: "Documentos", exact: true })
    );
    expect(
      await screen.findByRole("heading", {
        name: "Expediente documental del docente",
      })
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(documentsServiceMock.listTeacherRecords).toHaveBeenCalledWith(
        "teacher-1",
        expect.objectContaining({ page: 1 })
      )
    );
  });

  test("editar el puesto recarga la página filtrada sin mantener filas fuera del filtro", async () => {
    const updated = { ...SAMPLE[0], position: "Orientador/a" };
    teachersServiceMock.listPage
      .mockResolvedValueOnce(paged([SAMPLE[0]]))
      .mockResolvedValue(paged([]));
    teachersServiceMock.update.mockResolvedValue(updated);
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />, {
      route: "/app/docentes?position=Docente+Titulado&page_size=50",
    });
    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);
    await user.click(
      screen.getByRole("button", { name: "Editar", exact: true })
    );
    await selectOption(user, /^Puesto/, "Orientador/a");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await waitFor(() =>
      expect(teachersServiceMock.listPage).toHaveBeenCalledTimes(2)
    );
    expect(teachersServiceMock.listPage).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 50,
      position: "Docente Titulado",
    });
    await waitFor(() =>
      expect(
        within(screen.getByRole("table", { hidden: true })).queryByText(
          "Marvin Estuardo Lopez Cifuentes"
        )
      ).not.toBeInTheDocument()
    );
    expect(
      screen.getByRole("heading", { name: "Marvin Estuardo Lopez Cifuentes" })
    ).toBeInTheDocument();
  });

  test("opens and closes the photo lightbox from the detail panel", async () => {
    teachersServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
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

    const lightbox = await screen.findByRole("dialog", {
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
    teachersServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
    teachersServiceMock.nextCode.mockResolvedValue("DOC-013");
    const created = {
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
    teachersServiceMock.create.mockResolvedValue(created);
    teachersServiceMock.listPage
      .mockResolvedValueOnce(paged(SAMPLE))
      .mockResolvedValue(paged([...SAMPLE, created]));
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getByRole("button", { name: /Nuevo registro/ }));

    // Un `change` por campo y no tecleo letra por letra: cada pulsación vuelve
    // a renderizar el formulario entero. Las etiquetas se buscan dentro del
    // diálogo, no en toda la pantalla (ver `fillInstitutionalPerson`). Así la
    // prueba cabe holgada en el límite global aun con la suite en paralelo.
    const dialog = screen.getByRole("dialog");
    const form = within(dialog);
    const fill = (label, value) =>
      fireEvent.change(form.getByLabelText(label), { target: { value } });
    fill(/^Nombres/, "Nueva");
    fill(/^Apellidos/, "Docente");
    await fillInstitutionalPerson(user, dialog);
    fill(/^Especialidad/, "Fisica");
    await selectOption(user, /^Puesto/, "Docente Interino", dialog);
    // Llega prellenado con la sugerencia del backend, y se puede sobreescribir.
    expect(form.getByLabelText(/^Código de empleado/i)).toHaveValue("DOC-013");
    fill(/^Código de empleado/i, "EMP-0300");
    await user.click(form.getByRole("button", { name: /Crear registro/ }));

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
    expect(await screen.findByText("Nueva Docente")).toBeInTheDocument();
  });

  test("previews a newly selected photo in the create form", async () => {
    teachersServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
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
    teachersServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
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
  });

  test("requires the mandatory fields before submitting", async () => {
    teachersServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
    const user = userEvent.setup();
    renderWithRouter(<DocentesPage />);

    await screen.findByText("Marvin Estuardo Lopez Cifuentes");
    await user.click(screen.getByRole("button", { name: /Nuevo registro/ }));
    await user.click(screen.getByRole("button", { name: /Crear registro/ }));

    expect(screen.getByText(/Complete el campo/)).toBeInTheDocument();
    expect(teachersServiceMock.create).not.toHaveBeenCalled();
  });
});
