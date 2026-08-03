import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { PadresPage } from "../pages/PadresPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const guardiansServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  create: vi.fn(),
}));

vi.mock("../services/guardiansService.js", () => ({
  guardiansService: guardiansServiceMock,
}));

const downloadCsvMock = vi.hoisted(() => vi.fn());

vi.mock("../utils/csv.js", () => ({ downloadCsv: downloadCsvMock }));

const SAMPLE = [
  {
    id: 1,
    first_name: "Rosa Elvira",
    last_name: "Garcia Mendez",
    occupation: "Comerciante",
    phone_number: "4512-7890",
    assigned_students: [
      {
        student_id: 1,
        full_name: "Maria Jose Lopez Garcia",
        section: { grade: "3ro", name: "A" },
        relationship_label: "Madre",
        is_primary: true,
      },
    ],
  },
  {
    id: 2,
    first_name: "Marco Tulio",
    last_name: "Ramirez Us",
    occupation: "Agricultor",
    phone_number: "3398-1122",
    assigned_students: [
      {
        student_id: 2,
        full_name: "Carlos Enrique Ramirez Perez",
        section: { grade: "2do", name: "B" },
        relationship_label: "Padre",
        is_primary: true,
      },
    ],
  },
];

describe("PadresPage", () => {
  beforeEach(() => {
    guardiansServiceMock.list.mockReset();
    guardiansServiceMock.create.mockReset();
    downloadCsvMock.mockReset();
  });

  test("exports the currently filtered rows as CSV", async () => {
    guardiansServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<PadresPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getByRole("button", { name: "Exportar CSV" }));

    expect(downloadCsvMock).toHaveBeenCalledTimes(1);
    const [filename, , rows] = downloadCsvMock.mock.calls[0];
    expect(filename).toBe("padres-de-familia.csv");
    expect(rows).toEqual(SAMPLE);
  });

  test("renders the list once loaded", async () => {
    guardiansServiceMock.list.mockResolvedValue(SAMPLE);
    renderWithRouter(<PadresPage />);

    expect(
      await screen.findByText("Rosa Elvira Garcia Mendez")
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("table")).getByText('1 alumno — 3ro "A"')
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Mostrando 1-2 de 2 registros/)
    ).toBeInTheDocument();
  });

  test("shows an empty state when the search does not match", async () => {
    guardiansServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<PadresPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.type(
      screen.getByPlaceholderText("Buscar por nombre..."),
      "Nadie"
    );

    expect(
      screen.getByText(
        "No hay padres o encargados que coincidan con la busqueda."
      )
    ).toBeInTheDocument();
  });

  test("filters by the assigned student's seccion", async () => {
    guardiansServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<PadresPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.selectOptions(screen.getByLabelText("Filtrar"), '2do "B"');

    expect(
      screen.queryByText("Rosa Elvira Garcia Mendez")
    ).not.toBeInTheDocument();
    expect(screen.getByText("Marco Tulio Ramirez Us")).toBeInTheDocument();
  });

  test("shows the service error instead of the table", async () => {
    guardiansServiceMock.list.mockRejectedValue(
      new Error("Solicitud no completada.")
    );
    renderWithRouter(<PadresPage />);

    expect(
      await screen.findByText("Solicitud no completada.")
    ).toBeInTheDocument();
  });

  test("opens the detail panel listing the assigned students", async () => {
    guardiansServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<PadresPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getAllByRole("button", { name: "Ver detalle" })[0]);

    const panel = screen.getByRole("complementary");
    expect(
      within(panel).getByRole("heading", { name: "Rosa Elvira Garcia Mendez" })
    ).toBeInTheDocument();
    expect(
      within(panel).getByText(/Maria Jose Lopez Garcia/)
    ).toBeInTheDocument();
  });

  test("submits the create form against the mock service", async () => {
    guardiansServiceMock.list.mockResolvedValue(SAMPLE);
    guardiansServiceMock.create.mockResolvedValue({
      id: 3,
      first_name: "Nuevo Encargado",
      last_name: "",
      occupation: "Panadero",
      phone_number: "4000-0000",
      assigned_students: [],
    });
    const user = userEvent.setup();
    renderWithRouter(<PadresPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getByRole("button", { name: "+ Agregar nuevo" }));

    await user.type(
      screen.getByLabelText("Nombres completos"),
      "Nuevo Encargado"
    );
    await user.type(screen.getByLabelText("Ocupacion"), "Panadero");
    await user.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() =>
      expect(guardiansServiceMock.create).toHaveBeenCalledTimes(1)
    );
    expect(guardiansServiceMock.create).toHaveBeenCalledWith(
      expect.objectContaining({
        first_name: "Nuevo Encargado",
        last_name: "",
        occupation: "Panadero",
        assigned_students: [],
      })
    );
    expect(await screen.findByText("Nuevo Encargado")).toBeInTheDocument();
  });

  test("requires the mandatory fields before submitting", async () => {
    guardiansServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<PadresPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getByRole("button", { name: "+ Agregar nuevo" }));
    await user.click(screen.getByRole("button", { name: "Guardar" }));

    expect(screen.getByText(/es obligatorio/)).toBeInTheDocument();
    expect(guardiansServiceMock.create).not.toHaveBeenCalled();
  });
});
