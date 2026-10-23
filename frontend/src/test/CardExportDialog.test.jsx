import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const attendanceServiceMock = vi.hoisted(() => ({
  previewCardExport: vi.fn(),
  exportCards: vi.fn(),
}));
const studentsServiceMock = vi.hoisted(() => ({ listPage: vi.fn() }));
const downloadMock = vi.hoisted(() => vi.fn());

vi.mock("@attendance/attendanceService.js", async () => {
  const actual = await vi.importActual("@attendance/attendanceService.js");
  return { ...actual, attendanceService: attendanceServiceMock };
});
vi.mock("@students/studentsService.js", () => ({
  studentsService: studentsServiceMock,
}));
vi.mock("@shared/utils/download.js", async (importOriginal) => ({
  ...(await importOriginal()),
  downloadResponseFile: downloadMock,
}));
vi.mock("@shared/catalogs/academicCatalogs.js", async (importOriginal) => {
  const catalog = (options) => () => ({ options, loading: false, error: "" });
  return {
    ...(await importOriginal()),
    useCycleCatalog: catalog([
      { value: "c-old", label: "2025 · Cerrado", status: "closed" },
      { value: "c-1", label: "2026 · Activo", status: "active" },
    ]),
    useGradeCatalog: catalog([
      {
        value: "g-1",
        label: "Primero · Básico",
        levelId: "l-1",
        levelName: "Básico",
      },
      {
        value: "g-4",
        label: "Cuarto · Diversificado",
        levelId: "l-2",
        levelName: "Diversificado",
      },
    ]),
    useSectionCatalog: catalog([
      { value: "s-a", label: "Primero A", cycleId: "c-1", gradeId: "g-1" },
      { value: "s-old", label: "Primero Z", cycleId: "c-old", gradeId: "g-1" },
      { value: "s-d", label: "Cuarto A", cycleId: "c-1", gradeId: "g-4" },
    ]),
  };
});

import { CardExportDialog } from "@attendance/CardExportDialog.jsx";

import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const student = (n) => ({
  public_id: `s-${n}`,
  student_code: `EST-${n}`,
  person: { first_name: "Alumno", last_name: `${n}` },
});
const students = (count, from = 1) =>
  Array.from({ length: count }, (_, index) => student(from + index));
const paged = (results, count = results.length, next = null) => ({
  results,
  count,
  next,
  previous: null,
});

/** Simula el backend: `rows` filtrado por búsqueda y paginado. */
function serveStudents(rows) {
  studentsServiceMock.listPage.mockImplementation(async (params) => {
    const term = params.search ?? "";
    const matching = rows.filter((row) => row.student_code.includes(term));
    const size = params.page_size ?? 25;
    const start = (params.page - 1) * size;
    const results = matching.slice(start, start + size);
    const next = start + size < matching.length ? "next" : null;
    return paged(results, matching.length, next);
  });
}

const PREVIEW = {
  summary: { total: 3, ready: 1, to_issue: 1, skipped: 1 },
  rows: [
    {
      student_id: "s-1",
      full_name: "Ana Perez",
      student_code: "EST-1",
      status: "ready",
      reason: "",
    },
    {
      student_id: "s-2",
      full_name: "Beto Lopez",
      student_code: "EST-2",
      status: "to_issue",
      reason: "",
    },
    {
      student_id: "s-3",
      full_name: "Carla Ruiz",
      student_code: "EST-3",
      status: "skipped",
      reason: "Sin matrícula activa.",
    },
  ],
};

beforeEach(() => {
  Object.values(attendanceServiceMock).forEach((mock) => mock.mockReset());
  studentsServiceMock.listPage.mockReset();
  downloadMock.mockReset();
  serveStudents(students(3));
});

function renderDialog(props = {}) {
  const user = userEvent.setup();
  renderWithRouter(<CardExportDialog onClose={vi.fn()} open {...props} />);
  return user;
}

const checkbox = (n) =>
  screen.findByRole("checkbox", { name: `Seleccionar a Alumno ${n}` });
const status = () => screen.getByText(/seleccionados \(máximo 100\)/);

async function pick(user, name, option) {
  await user.click(screen.getByRole("combobox", { name }));
  await user.click(await screen.findByRole("option", { name: option }));
}

async function optionsOf(user, name) {
  await user.click(screen.getByRole("combobox", { name }));
  const listbox = await screen.findByRole("listbox");
  const labels = within(listbox)
    .getAllByRole("option")
    .map((option) => option.textContent);
  await user.keyboard("{Escape}");
  await waitFor(() =>
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument()
  );
  return labels;
}

describe("CardExportDialog", () => {
  test("filtra en cascada nivel → grado → sección del ciclo activo", async () => {
    const user = renderDialog();
    await checkbox(1);

    expect(await optionsOf(user, "Grado")).toEqual([
      "Todos los grados",
      "Primero · Básico",
      "Cuarto · Diversificado",
    ]);
    // Sin la sección del ciclo cerrado.
    expect(await optionsOf(user, "Sección")).toEqual([
      "Todas las secciones",
      "Primero A",
      "Cuarto A",
    ]);

    await pick(user, "Nivel", "Básico");
    expect(await optionsOf(user, "Grado")).toEqual([
      "Todos los grados",
      "Primero · Básico",
    ]);
    expect(await optionsOf(user, "Sección")).toEqual([
      "Todas las secciones",
      "Primero A",
    ]);

    await pick(user, "Sección", "Primero A");
    await waitFor(() =>
      expect(studentsServiceMock.listPage).toHaveBeenLastCalledWith({
        page: 1,
        level: "l-1",
        grade: "",
        section: "s-a",
        search: "",
      })
    );

    // Cambiar el nivel limpia grado y sección.
    await pick(user, "Nivel", "Diversificado");
    await waitFor(() =>
      expect(studentsServiceMock.listPage).toHaveBeenLastCalledWith(
        expect.objectContaining({ level: "l-2", grade: "", section: "" })
      )
    );
  });

  test("la selección uno a uno sobrevive a cambiar de página y de filtro", async () => {
    serveStudents(students(30));
    const user = renderDialog();

    await user.click(await checkbox(1));
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await user.click(await checkbox(26));
    expect(status()).toHaveTextContent("2 seleccionados");

    await user.type(
      screen.getByPlaceholderText("Buscar por nombre o código…"),
      "EST-3"
    );
    await waitFor(() =>
      expect(studentsServiceMock.listPage).toHaveBeenLastCalledWith(
        expect.objectContaining({ page: 1, search: "EST-3" })
      )
    );
    await user.click(await checkbox(30));
    expect(status()).toHaveTextContent("3 seleccionados");
    expect(screen.getByRole("dialog")).toHaveAccessibleName(
      /Exportar carnés \(3\)/
    );

    await user.click(screen.getByRole("button", { name: "Quitar selección" }));
    expect(status()).toHaveTextContent("0 seleccionados");
    expect(screen.getByRole("button", { name: "Continuar" })).toBeDisabled();
  });

  test("selecciona todos los del filtro recorriendo todas las páginas", async () => {
    serveStudents(students(60));
    const user = renderDialog();

    await user.click(
      await screen.findByRole("button", {
        name: "Seleccionar los 60 del filtro",
      })
    );

    await waitFor(() => expect(status()).toHaveTextContent("60 seleccionados"));
    expect(studentsServiceMock.listPage).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1, page_size: 100 })
    );
  });

  test("respeta el máximo de 100 al seleccionar todo el filtro", async () => {
    serveStudents([
      ...students(100),
      { ...student(500), student_code: "OTRO-500" },
    ]);
    const user = renderDialog();
    const search = () =>
      screen.getByPlaceholderText("Buscar por nombre o código…");

    // 101 en el filtro: ni siquiera se ofrece.
    expect(
      await screen.findByRole("button", {
        name: "Seleccionar los 101 del filtro",
      })
    ).toBeDisabled();
    expect(screen.getByText(/acótelo a 100 o menos/)).toBeInTheDocument();

    // 100 en el filtro más uno ya elegido fuera de él: se rechaza y se explica.
    await user.type(search(), "OTRO");
    await user.click(await checkbox(500));
    await user.clear(search());
    await user.type(search(), "EST");
    await user.click(
      await screen.findByRole("button", {
        name: "Seleccionar los 100 del filtro",
      })
    );

    expect(
      await screen.findByText(/serían 101 estudiantes y el máximo/)
    ).toBeInTheDocument();
    expect(status()).toHaveTextContent("1 seleccionados");
  });

  test("selecciona, elige formato, muestra la vista previa y descarga", async () => {
    attendanceServiceMock.previewCardExport.mockResolvedValue(PREVIEW);
    const file = { blob: new Blob(["zip"]), headers: new Headers() };
    attendanceServiceMock.exportCards.mockResolvedValue(file);
    const onExported = vi.fn();
    const user = renderDialog({ onExported });

    expect(screen.getByRole("button", { name: "Continuar" })).toBeDisabled();
    await user.click(
      await screen.findByRole("button", {
        name: "Seleccionar los 3 del filtro",
      })
    );
    await waitFor(() => expect(status()).toHaveTextContent("3 seleccionados"));
    await user.click(screen.getByRole("button", { name: "Continuar" }));

    expect(screen.getByText(/Paso 2 de 3/)).toBeInTheDocument();
    await user.click(
      screen.getByRole("combobox", { name: "Formato del archivo" })
    );
    // PNG solo existe con un único estudiante.
    expect(
      screen.queryByRole("option", { name: /PNG \(la imagen/ })
    ).toBeNull();
    await user.click(await screen.findByRole("option", { name: /ZIP/ }));
    await user.click(screen.getByRole("button", { name: "Ver vista previa" }));

    expect(attendanceServiceMock.previewCardExport).toHaveBeenCalledWith(
      ["s-1", "s-2", "s-3"],
      "zip"
    );
    expect(await screen.findByText("Se emitirá")).toBeInTheDocument();
    expect(screen.getByText("Omitido")).toBeInTheDocument();
    expect(screen.getByText("Sin matrícula activa.")).toBeInTheDocument();
    expect(screen.getByText(/1 se emitirán al confirmar/)).toBeInTheDocument();
    expect(attendanceServiceMock.exportCards).not.toHaveBeenCalled();

    await user.click(
      screen.getByRole("button", { name: "Confirmar y descargar" })
    );
    await waitFor(() =>
      expect(downloadMock).toHaveBeenCalledWith(file, "carnes.zip")
    );
    expect(attendanceServiceMock.exportCards).toHaveBeenCalledWith(
      ["s-1", "s-2", "s-3"],
      "zip"
    );
    expect(onExported).toHaveBeenCalled();
    expect(
      await screen.findByText(/Se descargó el archivo/)
    ).toBeInTheDocument();
  });

  test("con un solo estudiante ofrece PNG y no permite confirmar si nada es exportable", async () => {
    attendanceServiceMock.previewCardExport.mockResolvedValue({
      summary: { total: 1, ready: 0, to_issue: 0, skipped: 1 },
      rows: [PREVIEW.rows[2]],
    });
    const user = renderDialog();

    await user.click(await checkbox(3));
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    await pick(user, "Formato del archivo", /PNG \(la imagen/);
    await user.click(screen.getByRole("button", { name: "Ver vista previa" }));

    expect(attendanceServiceMock.previewCardExport).toHaveBeenCalledWith(
      ["s-3"],
      "png"
    );
    expect(
      await screen.findByText(/Ningún estudiante seleccionado/)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Confirmar y descargar" })
    ).toBeDisabled();
  });
});
