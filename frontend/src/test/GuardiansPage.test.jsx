import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { useLocation } from "react-router-dom";
import { selectOption } from "./helpers/selectOption.jsx";

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
  return <output data-testid="location">{location.search}</output>;
}

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
    guardiansServiceMock.listPage.mockReset().mockResolvedValue(paged(SAMPLE));
    guardiansServiceMock.create.mockReset();
    guardiansServiceMock.update.mockReset();
    downloadCsvMock.mockReset();
  });

  test("renders the list once loaded", async () => {
    guardiansServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
    renderWithRouter(<GuardiansPage />);

    expect(
      await screen.findByText("Rosa Elvira Garcia Mendez")
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("table")).getByText("rosa@example.test")
    ).toBeInTheDocument();
    expect(screen.getByText(/Mostrando 1–2 de 2/)).toBeInTheDocument();
  });

  test("consulta una página y recupera búsqueda, tamaño y actividad desde URL", async () => {
    guardiansServiceMock.listPage.mockResolvedValue(paged(SAMPLE, 2500));
    renderWithRouter(<GuardiansPage />, {
      route:
        "/app/padres-de-familia?page=2&page_size=50&search=Rosa&include_inactive=1",
    });
    await screen.findByText("Rosa Elvira Garcia Mendez");
    expect(guardiansServiceMock.listPage).toHaveBeenCalledExactlyOnceWith({
      page: 2,
      page_size: 50,
      search: "Rosa",
      include_inactive: true,
    });
    expect(guardiansServiceMock.list).not.toHaveBeenCalled();
    expect(screen.getByText(/2500 encargados encontrados/)).toBeInTheDocument();
    expect(
      screen.getByRole("switch", { name: "Mostrar desactivados" })
    ).toBeChecked();
  });

  test("pagina, cambia tamaño y busca en el servidor sin perder letras", async () => {
    guardiansServiceMock.listPage.mockResolvedValue(paged(SAMPLE, 2500));
    const user = userEvent.setup();
    renderWithRouter(
      <>
        <GuardiansPage />
        <LocationProbe />
      </>
    );
    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await waitFor(() =>
      expect(guardiansServiceMock.listPage).toHaveBeenLastCalledWith({
        page: 2,
        page_size: 25,
      })
    );
    await selectOption(user, /Filas por página/, "50");
    await waitFor(() =>
      expect(guardiansServiceMock.listPage).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 50,
      })
    );
    await user.type(
      screen.getByPlaceholderText(/Buscar por nombre/),
      "Rosa Elvira"
    );
    expect(screen.getByRole("button", { name: "Exportar CSV" })).toBeDisabled();
    await waitFor(() =>
      expect(guardiansServiceMock.listPage).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 50,
        search: "Rosa Elvira",
      })
    );
    expect(screen.getByPlaceholderText(/Buscar por nombre/)).toHaveValue(
      "Rosa Elvira"
    );
    expect(screen.getByTestId("location")).toHaveTextContent(
      "search=Rosa+Elvira"
    );
  });

  test("combina actividad y búsqueda, muestra desactivados y limpia conservando tamaño", async () => {
    guardiansServiceMock.listPage.mockResolvedValue(
      paged([{ ...SAMPLE[0], is_active: false }])
    );
    const user = userEvent.setup();
    renderWithRouter(
      <>
        <GuardiansPage />
        <LocationProbe />
      </>,
      { route: "/app/padres-de-familia?page=3&page_size=50&search=Rosa" }
    );
    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(
      screen.getByRole("switch", { name: "Mostrar desactivados" })
    );
    await waitFor(() =>
      expect(guardiansServiceMock.listPage).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 50,
        search: "Rosa",
        include_inactive: true,
      })
    );
    expect(await screen.findByText("Desactivado")).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Limpiar", exact: true })
    );
    await waitFor(() =>
      expect(guardiansServiceMock.listPage).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 50,
      })
    );
    expect(screen.getByTestId("location")).toHaveTextContent("?page_size=50");
  });

  test("exporta 1001 filas con los filtros vigentes sin recorrer el padrón al abrir", async () => {
    const rows = Array.from({ length: 1001 }, (_, index) => ({
      ...SAMPLE[0],
      id: index + 1,
      is_active: index !== 1000,
      person: { ...SAMPLE[0].person, last_name: `Demostracion ${index + 1}` },
    }));
    guardiansServiceMock.listPage.mockImplementation(
      async ({ page, page_size }) =>
        paged(
          rows.slice((page - 1) * page_size, page * page_size),
          rows.length,
          page * page_size < rows.length ? "next" : null
        )
    );
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />, {
      route:
        "/app/padres-de-familia?page=2&search=Demostracion&include_inactive=1",
    });
    await screen.findByText("Rosa Elvira Demostracion 26");
    expect(guardiansServiceMock.listPage).toHaveBeenCalledTimes(1);
    expect(downloadCsvMock).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Exportar CSV" }));
    await waitFor(() => expect(downloadCsvMock).toHaveBeenCalledTimes(1));
    const [filename, csv] = downloadCsvMock.mock.calls[0];
    expect(filename).toBe("padres-de-familia.csv");
    expect(csv).toContain("Rosa Elvira Demostracion 1001");
    expect(csv).toContain("Desactivado");
    expect(csv.trim().split(/\r?\n/)).toHaveLength(1002);
    const calls = guardiansServiceMock.listPage.mock.calls.slice(1);
    expect(calls).toHaveLength(11);
    calls.forEach(([params], index) =>
      expect(params).toEqual({
        page: index + 1,
        page_size: 100,
        search: "Demostracion",
        include_inactive: true,
      })
    );
  });

  test("una página ya inexistente permite volver a la primera sin eliminar filtros", async () => {
    guardiansServiceMock.listPage
      .mockRejectedValueOnce(new Error("Página no disponible."))
      .mockResolvedValue(paged(SAMPLE));
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />, {
      route: "/app/padres-de-familia?page=9&search=Rosa&include_inactive=1",
    });
    await screen.findByText("Página no disponible.");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Volver a primera página" })
    );
    await screen.findByText("Rosa Elvira Garcia Mendez");
    expect(guardiansServiceMock.listPage).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 25,
      search: "Rosa",
      include_inactive: true,
    });
  });

  test("shows an empty state when the search does not match", async () => {
    guardiansServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    guardiansServiceMock.listPage.mockResolvedValue(paged([]));
    await user.type(screen.getByPlaceholderText(/Buscar por nombre/), "Nadie");

    expect(
      await screen.findByText("Sin encargados para los filtros seleccionados.")
    ).toBeInTheDocument();
  });

  test("shows the service error instead of the table", async () => {
    guardiansServiceMock.listPage.mockRejectedValue(
      new Error("Solicitud no completada.")
    );
    renderWithRouter(<GuardiansPage />);

    expect(
      await screen.findByText("Solicitud no completada.")
    ).toBeInTheDocument();
    guardiansServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
    await userEvent
      .setup()
      .click(screen.getByRole("button", { name: "Reintentar listado" }));
    expect(
      await screen.findByText("Rosa Elvira Garcia Mendez")
    ).toBeInTheDocument();
  });

  test("opens the detail panel for a row", async () => {
    guardiansServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
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
    guardiansServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
    const created = {
      id: 3,
      person: {
        public_id: "person-33",
        first_name: "Nuevo",
        last_name: "Encargado",
        email: "",
        phone_number: "",
      },
    };
    guardiansServiceMock.create.mockResolvedValue(created);
    guardiansServiceMock.listPage
      .mockResolvedValueOnce(paged(SAMPLE))
      .mockResolvedValue(paged([...SAMPLE, created]));
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
    expect(await screen.findByText("Nuevo Encargado")).toBeInTheDocument();
  }, 10000);

  test("edits a guardian and refreshes the filtered page without inserting a local row", async () => {
    guardiansServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
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
    renderWithRouter(<GuardiansPage />, {
      route: "/app/padres-de-familia?search=Mendez",
    });

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getAllByRole("button", { name: /Ver detalle/ })[0]);
    await user.click(screen.getByRole("button", { name: "Editar" }));
    guardiansServiceMock.listPage.mockResolvedValue(paged([]));

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
    await waitFor(() =>
      expect(guardiansServiceMock.listPage).toHaveBeenCalledTimes(2)
    );
    expect(guardiansServiceMock.listPage).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: "Mendez", page: 1 })
    );
    expect(
      await screen.findByText("Sin encargados para los filtros seleccionados.")
    ).toBeInTheDocument();
  });

  test("requires the mandatory fields before submitting", async () => {
    guardiansServiceMock.listPage.mockResolvedValue(paged(SAMPLE));
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);

    await screen.findByText("Rosa Elvira Garcia Mendez");
    await user.click(screen.getByRole("button", { name: /Nuevo encargado/ }));
    await user.click(screen.getByRole("button", { name: /Crear encargado/ }));

    expect(screen.getByText(/Complete el campo/)).toBeInTheDocument();
    expect(guardiansServiceMock.create).not.toHaveBeenCalled();
  });
});
