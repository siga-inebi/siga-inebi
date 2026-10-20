import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { GuardiansPage } from "@guardians/GuardiansPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import {
  editInstitutionalPerson,
  editedInstitutionalPerson,
  fillInstitutionalPerson,
  institutionalPerson,
  visibleInstitutionalPerson,
} from "./helpers/institutionalPerson.js";

const guardiansServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
  listPage: vi.fn(),
  get: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
}));

vi.mock("@guardians/guardiansService.js", () => ({
  guardiansService: guardiansServiceMock,
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
      public_id: "person-31",
      first_name: "Rosa Elvira",
      last_name: "Garcia Mendez",
      email: "rosa@example.test",
      phone_number: "4512-7890",
    },
  },
  {
    id: 2,
    person: {
      public_id: "person-32",
      first_name: "Marco Tulio",
      last_name: "Ramirez Us",
      email: "marco@example.test",
      phone_number: "3398-1122",
    },
  },
];

describe("GuardiansPage", () => {
  beforeEach(() => {
    guardiansServiceMock.list.mockReset();
    guardiansServiceMock.listPage.mockReset();
    guardiansServiceMock.create.mockReset();
    guardiansServiceMock.update.mockReset();
    downloadCsvMock.mockReset();
  });

  test("exports every page of the current search as CSV", async () => {
    guardiansServiceMock.listPage.mockResolvedValue(page(SAMPLE));
    guardiansServiceMock.list.mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />, { route: "/?search=Garcia" });

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getByRole("button", { name: "Exportar CSV" }));

    await waitFor(() => expect(downloadCsvMock).toHaveBeenCalledTimes(1));
    expect(guardiansServiceMock.list).toHaveBeenCalledWith({
      search: "Garcia",
    });
    const [filename, , rows] = downloadCsvMock.mock.calls[0];
    expect(filename).toBe("padres-de-familia.csv");
    expect(rows).toEqual(SAMPLE);
  });

  test("asks the server only for the visible page and shows its total", async () => {
    guardiansServiceMock.listPage.mockResolvedValue(page(SAMPLE, 100));
    renderWithRouter(<GuardiansPage />);

    expect(
      await screen.findByText("Rosa Elvira Garcia Mendez")
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("table")).getByText("rosa@example.test")
    ).toBeInTheDocument();
    expect(guardiansServiceMock.listPage).toHaveBeenCalledTimes(1);
    expect(guardiansServiceMock.listPage).toHaveBeenCalledWith({
      page: 1,
      page_size: 25,
    });
    expect(guardiansServiceMock.list).not.toHaveBeenCalled();
    expect(screen.getByText("100 encargados registrados.")).toBeInTheDocument();
  });

  test("sends the search to the server and shows its empty state", async () => {
    guardiansServiceMock.listPage.mockImplementation(async (params) =>
      params.search ? page([]) : page(SAMPLE)
    );
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.type(
      screen.getByPlaceholderText("Buscar por nombre o CUI…"),
      "Nadie"
    );

    expect(
      await screen.findByText("Sin resultados para la busqueda.")
    ).toBeInTheDocument();
    expect(guardiansServiceMock.listPage).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 25,
      search: "Nadie",
    });
  });

  test("shows the service error instead of the table", async () => {
    guardiansServiceMock.listPage.mockRejectedValue(
      new Error("Solicitud no completada.")
    );
    renderWithRouter(<GuardiansPage />);

    expect(
      await screen.findByText("Solicitud no completada.")
    ).toBeInTheDocument();
  });

  test("opens the detail panel for a row", async () => {
    guardiansServiceMock.listPage.mockResolvedValue(page(SAMPLE));
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);

    const panel = screen.getByRole("dialog");
    expect(
      within(panel).getByRole("heading", { name: "Rosa Elvira Garcia Mendez" })
    ).toBeInTheDocument();
    expect(within(panel).getByText("rosa@example.test")).toBeInTheDocument();
  });

  test("submits the create form against the service", async () => {
    const createdGuardian = {
      id: 3,
      person: {
        public_id: "person-33",
        first_name: "Nuevo",
        last_name: "Encargado",
        email: "",
        phone_number: "",
      },
    };
    guardiansServiceMock.listPage
      .mockResolvedValueOnce(page(SAMPLE))
      .mockResolvedValueOnce(page([...SAMPLE, createdGuardian]));
    guardiansServiceMock.create.mockResolvedValue(createdGuardian);
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getByRole("button", { name: /Nuevo encargado/ }));

    await user.type(screen.getByLabelText(/^Nombres/), "Nuevo");
    await user.type(screen.getByLabelText(/^Apellidos/), "Encargado");
    await fillInstitutionalPerson(user);
    await user.click(screen.getByRole("button", { name: /Crear encargado/ }));

    await waitFor(() =>
      expect(guardiansServiceMock.create).toHaveBeenCalledTimes(1)
    );
    expect(guardiansServiceMock.create).toHaveBeenCalledWith(
      expect.objectContaining({
        person: {
          ...institutionalPerson,
          first_name: "Nuevo",
          last_name: "Encargado",
        },
      })
    );
    await waitFor(() =>
      expect(guardiansServiceMock.listPage).toHaveBeenCalledTimes(2)
    );
    expect(await screen.findByText("Nuevo Encargado")).toBeInTheDocument();
  }, 10000);

  test("edits a guardian via the detail panel", async () => {
    guardiansServiceMock.listPage.mockResolvedValue(page(SAMPLE));
    guardiansServiceMock.update.mockResolvedValue({
      id: 1,
      person: {
        ...visibleInstitutionalPerson,
        ...editedInstitutionalPerson,
        public_id: "person-31",
        first_name: "Rosa Elvira",
        last_name: "Garcia Lopez",
        email: "rosa@example.test",
        phone_number: "4512-7890",
      },
    });
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);
    await user.click(screen.getByRole("button", { name: "Editar" }));

    const lastNameInput = screen.getByLabelText(/^Apellidos/);
    expect(lastNameInput).toHaveValue("Garcia Mendez");
    await user.clear(lastNameInput);
    await user.type(lastNameInput, "Garcia Lopez");
    expect(screen.queryByLabelText(/^CUI/)).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText(/^Fecha de nacimiento/)
    ).not.toBeInTheDocument();
    await editInstitutionalPerson(user);
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() =>
      expect(guardiansServiceMock.update).toHaveBeenCalledTimes(1)
    );
    expect(guardiansServiceMock.update).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        person: {
          ...visibleInstitutionalPerson,
          ...editedInstitutionalPerson,
          public_id: "person-31",
          first_name: "Rosa Elvira",
          last_name: "Garcia Lopez",
          email: "rosa@example.test",
          phone_number: "4512-7890",
        },
      })
    );
    expect(
      await screen.findByRole("heading", { name: "Rosa Elvira Garcia Lopez" })
    ).toBeInTheDocument();
  });

  test("requires the mandatory fields before submitting", async () => {
    guardiansServiceMock.listPage.mockResolvedValue(page(SAMPLE));
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getByRole("button", { name: /Nuevo encargado/ }));
    await user.click(screen.getByRole("button", { name: /Crear encargado/ }));

    expect(screen.getByText(/Complete el campo/)).toBeInTheDocument();
    expect(guardiansServiceMock.create).not.toHaveBeenCalled();
  });
});
