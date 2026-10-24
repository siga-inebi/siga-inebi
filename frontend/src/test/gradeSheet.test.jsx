import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useLocation } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

const evaluationServiceMock = vi.hoisted(() => ({
  listUnits: vi.fn(),
  getSheet: vi.fn(),
  saveSheet: vi.fn(),
  getCaptureProgress: vi.fn(),
  listGradeCourses: vi.fn(),
  downloadCourseWorkbook: vi.fn(),
  importCourseWorkbook: vi.fn(),
}));
const cyclesServiceMock = vi.hoisted(() => ({ list: vi.fn() }));

vi.mock("@evaluation/evaluationService.js", async (importOriginal) => {
  const original = await importOriginal();
  return { ...original, evaluationService: evaluationServiceMock };
});
vi.mock("@cycles/cyclesService.js", async (importOriginal) => {
  const original = await importOriginal();
  return { ...original, cyclesService: cyclesServiceMock };
});
const downloadMock = vi.hoisted(() => ({ downloadResponseFile: vi.fn() }));
vi.mock("@shared/utils/download.js", async (importOriginal) => {
  const original = await importOriginal();
  return {
    ...original,
    downloadResponseFile: downloadMock.downloadResponseFile,
  };
});
vi.mock("@academics/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});

import { EvaluationPage } from "@evaluation/EvaluationPage.jsx";
import { paginated } from "./fixtures/academics.js";
import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";
import {
  academicsServiceMock,
  resetAcademicsServiceMock,
} from "./mocks/academicsService.js";

const TEACHER = sessionUser(["grade.write"]);
const CYCLE = {
  public_id: "c-2026",
  name: "Ciclo 2026",
  status: "active",
  year: 2026,
};
const UNIT = {
  public_id: "u-4",
  number: 4,
  name: "Cuarta unidad",
  status: "open",
  capture_starts_on: "2026-09-01",
  capture_ends_on: "2026-10-30",
};
const SECTION = {
  public_id: "sec-a",
  name: "A",
  grade: { public_id: "g-1", name: "Primero Básico" },
  shift: { public_id: "s-1", name: "Matutina" },
};
const MATH = { public_id: "sub-mat", name: "Matemática" };
const COURSE = {
  section: {
    public_id: "sec-a",
    label: "Primero Básico A · Matutina",
    grade_name: "Primero Básico",
  },
  subject: MATH,
  teacher_name: "Rosa Pérez",
};

const row = (id, name, code, grade = null) => ({
  enrolment_id: id,
  student: { public_id: `st-${id}`, student_code: code, full_name: name },
  grade,
});

const SHEET = {
  unit: {
    public_id: "u-4",
    name: "Cuarta unidad",
    status: "open",
    window_open: true,
    can_capture: true,
    capture_exception_expires_at: null,
  },
  section: { public_id: "sec-a", name: "Primero Básico A" },
  subject: MATH,
  teacher: { public_id: "p-7", name: "Rosa Pérez" },
  rows: [
    row("e-1", "Ana López", "EST-1", { public_id: "g-1", value: 80 }),
    row("e-2", "Bruno Díaz", "EST-2"),
    row("e-3", "Carla Ruiz", "EST-3"),
  ],
};

const SHEET_ROUTE =
  "/app/evaluacion?tab=planilla&unidad=u-4&seccion=sec-a&subarea=sub-mat";

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.search}</output>;
}

function renderPage(route = SHEET_ROUTE, user = TEACHER) {
  return renderWithSession(
    <>
      <EvaluationPage />
      <LocationProbe />
    </>,
    { user, route }
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  resetAcademicsServiceMock();
  cyclesServiceMock.list.mockResolvedValue(paginated([CYCLE]));
  evaluationServiceMock.listUnits.mockResolvedValue(paginated([UNIT]));
  evaluationServiceMock.getSheet.mockResolvedValue(SHEET);
  evaluationServiceMock.listGradeCourses.mockResolvedValue([COURSE]);
  academicsServiceMock.listSections.mockResolvedValue(paginated([SECTION]));
  academicsServiceMock.listCurriculumPlans.mockResolvedValue(
    paginated([{ public_id: "plan-1", grade: SECTION.grade, subject: MATH }])
  );
});

describe("Planilla de calificaciones (V2, V8)", () => {
  test("carga la planilla de la URL con el docente inferido y sin selector de docente", async () => {
    renderPage();

    expect(await screen.findByText("Rosa Pérez")).toBeInTheDocument();
    expect(evaluationServiceMock.getSheet).toHaveBeenCalledWith(
      "c-2026",
      "u-4",
      "sec-a",
      "sub-mat"
    );
    // Las opciones salen de los cursos que la cuenta califica, no de todas las
    // secciones del ciclo ni del plan de estudios.
    expect(evaluationServiceMock.listGradeCourses).toHaveBeenCalledWith(
      "c-2026"
    );
    expect(academicsServiceMock.listSections).not.toHaveBeenCalled();
    expect(academicsServiceMock.listCurriculumPlans).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Nota de Ana López")).toHaveValue("80");
    expect(screen.getByLabelText("Nota de Bruno Díaz")).toHaveValue("");
    expect(screen.queryByLabelText(/^Docente/)).toBeNull();
    expect(
      screen.getByRole("button", { name: "Guardar cambios" })
    ).toBeDisabled();
  });

  test("Enter y las flechas mueven entre filas", async () => {
    const user = userEvent.setup();
    renderPage();

    const first = await screen.findByLabelText("Nota de Ana López");
    await user.click(first);
    await user.keyboard("{Enter}");
    expect(screen.getByLabelText("Nota de Bruno Díaz")).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    expect(screen.getByLabelText("Nota de Carla Ruiz")).toHaveFocus();
    await user.keyboard("{ArrowUp}");
    expect(screen.getByLabelText("Nota de Bruno Díaz")).toHaveFocus();
  });

  test("guarda solo las celdas que cambiaron y avisa el resultado", async () => {
    const user = userEvent.setup();
    evaluationServiceMock.saveSheet.mockResolvedValue({
      created: 1,
      updated: 1,
    });
    renderPage();

    const ana = await screen.findByLabelText("Nota de Ana López");
    await user.clear(ana);
    await user.type(ana, "85");
    await user.type(screen.getByLabelText("Nota de Carla Ruiz"), "70");
    await user.click(
      screen.getByRole("button", { name: "Guardar cambios (2)" })
    );

    await waitFor(() =>
      expect(evaluationServiceMock.saveSheet).toHaveBeenCalledWith(
        "c-2026",
        "u-4",
        {
          section_id: "sec-a",
          subject_id: "sub-mat",
          grades: [
            { enrolment_id: "e-1", value: 85 },
            { enrolment_id: "e-3", value: 70 },
          ],
        }
      )
    );
    expect(
      await screen.findByText("Se guardaron 2 notas (1 nuevas, 1 corregidas).")
    ).toBeInTheDocument();
  });

  test("valida en la celda antes de enviar", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(await screen.findByLabelText("Nota de Bruno Díaz"), "101");
    await user.click(
      screen.getByRole("button", { name: "Guardar cambios (1)" })
    );

    expect(
      await screen.findByText("Escriba un número entero de 0 a 100.")
    ).toBeInTheDocument();
    expect(evaluationServiceMock.saveSheet).not.toHaveBeenCalled();
  });

  test("el error de una fila del lote vuelve a su fila por índice", async () => {
    const user = userEvent.setup();
    const rejection = new Error("Solicitud no completada.");
    rejection.status = 400;
    rejection.payload = {
      errors: [
        {
          index: 1,
          student_code: "EST-3",
          field: "enrolment_id",
          message: "La matrícula no está activa en la sección.",
        },
      ],
    };
    evaluationServiceMock.saveSheet.mockRejectedValue(rejection);
    renderPage();

    await user.type(await screen.findByLabelText("Nota de Bruno Díaz"), "60");
    await user.type(screen.getByLabelText("Nota de Carla Ruiz"), "70");
    await user.click(
      screen.getByRole("button", { name: "Guardar cambios (2)" })
    );

    const carla = screen.getByLabelText("Nota de Carla Ruiz");
    expect(
      await screen.findByText("La matrícula no está activa en la sección.")
    ).toBeInTheDocument();
    expect(carla).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText("Nota de Bruno Díaz")).toHaveAttribute(
      "aria-invalid",
      "false"
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "No se guardó ninguna nota"
    );
  });

  test("un rechazo del lote (ventana, docente) se muestra como aviso", async () => {
    const user = userEvent.setup();
    evaluationServiceMock.saveSheet.mockRejectedValue(
      new Error("La ventana de captura de la unidad está cerrada.")
    );
    renderPage();

    await user.type(await screen.findByLabelText("Nota de Bruno Díaz"), "60");
    await user.click(
      screen.getByRole("button", { name: "Guardar cambios (1)" })
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "La ventana de captura de la unidad está cerrada."
    );
  });

  test("con la ventana cerrada la planilla es de solo consulta", async () => {
    evaluationServiceMock.getSheet.mockResolvedValue({
      ...SHEET,
      unit: { ...SHEET.unit, window_open: false, can_capture: false },
    });
    renderPage();

    expect(
      await screen.findByText(/hoy la planilla es de solo consulta/)
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Nota de Ana López")).toBeDisabled();
    expect(
      screen.queryByRole("button", { name: /Guardar cambios/ })
    ).toBeNull();
  });

  test("un permiso excepcional vigente habilita la planilla con la ventana cerrada", async () => {
    evaluationServiceMock.getSheet.mockResolvedValue({
      ...SHEET,
      unit: {
        ...SHEET.unit,
        status: "closed",
        window_open: false,
        can_capture: true,
        capture_exception_expires_at: "2026-10-20T23:59:00-06:00",
      },
    });
    renderPage();

    expect(
      await screen.findByText(/un permiso excepcional habilita la captura/)
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Nota de Ana López")).toBeEnabled();
    expect(screen.queryByText(/solo consulta/)).toBeNull();
  });

  test("sin docente asignado lo explica", async () => {
    evaluationServiceMock.getSheet.mockResolvedValue({
      ...SHEET,
      teacher: null,
    });
    renderPage();

    expect(await screen.findByText("Sin docente asignado")).toBeInTheDocument();
    expect(
      screen.getByText(/no tiene docente asignado en esta subárea/)
    ).toBeInTheDocument();
  });

  test("quien solo configura ve la planilla sin poder editar", async () => {
    renderPage(SHEET_ROUTE, sessionUser(["evaluation.configure_units"]));

    expect(
      await screen.findByText(/puede consultar la planilla, pero no registrar/)
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Nota de Ana López")).toBeDisabled();
  });
});

describe("Avance de captura (V3)", () => {
  test("muestra el avance y abre la planilla de una fila", async () => {
    const user = userEvent.setup();
    evaluationServiceMock.getCaptureProgress.mockResolvedValue({
      unit_public_id: "u-4",
      unit_name: "Cuarta unidad",
      window_open: true,
      overall_progress_pct: 50,
      rows: [
        {
          section: { public_id: "sec-a", name: "Primero Básico A" },
          subject: MATH,
          teacher: { public_id: "p-7", name: "Rosa Pérez" },
          students_total: 30,
          students_graded: 15,
          students_pending: 15,
          progress_pct: 50,
        },
      ],
    });
    renderPage("/app/evaluacion?tab=avance&unidad=u-4");

    expect(
      await screen.findByText("Avance de «Cuarta unidad»")
    ).toBeInTheDocument();
    expect(screen.getByText("15 de 30")).toBeInTheDocument();
    expect(
      screen.getByRole("progressbar", { name: "Avance general" })
    ).toHaveAttribute("aria-valuenow", "50");

    await user.click(
      screen.getByRole("button", {
        name: "Abrir planilla de Primero Básico A, Matemática",
      })
    );
    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent("tab=planilla")
    );
    const search = screen.getByTestId("location").textContent;
    expect(search).toContain("seccion=sec-a");
    expect(search).toContain("subarea=sub-mat");
    await waitFor(() =>
      expect(evaluationServiceMock.getSheet).toHaveBeenCalledWith(
        "c-2026",
        "u-4",
        "sec-a",
        "sub-mat"
      )
    );
    const panel = screen.getByRole("tabpanel", { name: "Planilla" });
    expect(await within(panel).findByText("Rosa Pérez")).toBeInTheDocument();
  });

  test("un 403 del avance se muestra como error", async () => {
    evaluationServiceMock.getCaptureProgress.mockRejectedValue(
      new Error("El actor no tiene el permiso requerido.")
    );
    renderPage("/app/evaluacion?tab=avance&unidad=u-4");

    expect(
      await screen.findByText("El actor no tiene el permiso requerido.")
    ).toBeInTheDocument();
  });
});

describe("Cursos del docente y carga por Excel", () => {
  const OTHER_COURSE = {
    section: {
      public_id: "sec-b",
      label: "Segundo Básico B · Matutina",
      grade_name: "Segundo Básico",
    },
    subject: { public_id: "sub-idi", name: "Idioma" },
    teacher_name: "Rosa Pérez",
  };

  test("solo ofrece las secciones y subáreas de los cursos de la cuenta", async () => {
    evaluationServiceMock.listGradeCourses.mockResolvedValue([
      COURSE,
      OTHER_COURSE,
    ]);
    const user = userEvent.setup();
    renderPage("/app/evaluacion?tab=planilla&unidad=u-4");

    await user.click(await screen.findByLabelText("Sección"));
    const sections = await screen.findByRole("listbox");
    expect(
      within(sections)
        .getAllByRole("option")
        .map((option) => option.textContent)
    ).toEqual([
      "Elija una sección",
      "Primero Básico A · Matutina",
      "Segundo Básico B · Matutina",
    ]);
    await user.click(
      within(sections).getByRole("option", {
        name: "Segundo Básico B · Matutina",
      })
    );

    await user.click(screen.getByLabelText("Subárea"));
    const subjects = await screen.findByRole("listbox");
    expect(
      within(subjects)
        .getAllByRole("option")
        .map((option) => option.textContent)
    ).toEqual(["Elija una subárea", "Idioma"]);
  });

  test("sin cursos explica que falta la asignación docente", async () => {
    evaluationServiceMock.listGradeCourses.mockResolvedValue([]);
    renderPage("/app/evaluacion?tab=planilla&unidad=u-4");

    expect(
      await screen.findByText(/no tiene cursos para calificar en este ciclo/)
    ).toBeInTheDocument();
  });

  test("descarga la plantilla del curso elegido", async () => {
    const file = { blob: new Blob(["x"]), headers: new Headers() };
    evaluationServiceMock.downloadCourseWorkbook.mockResolvedValue(file);
    const user = userEvent.setup();
    renderPage();

    await user.click(
      await screen.findByRole("button", { name: "Descargar plantilla" })
    );

    expect(evaluationServiceMock.downloadCourseWorkbook).toHaveBeenCalledWith(
      "c-2026",
      "sec-a",
      "sub-mat"
    );
    expect(downloadMock.downloadResponseFile).toHaveBeenCalledWith(
      file,
      "notas.xlsx"
    );
  });

  test("importa el Excel y resume lo registrado", async () => {
    evaluationServiceMock.importCourseWorkbook.mockResolvedValue({
      created: 3,
      updated: 1,
      unchanged: 2,
    });
    const user = userEvent.setup();
    renderPage();
    const excel = new File(["xlsx"], "notas.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    await user.upload(await screen.findByLabelText("Archivo de notas"), excel);

    expect(evaluationServiceMock.importCourseWorkbook).toHaveBeenCalledWith(
      "c-2026",
      "sec-a",
      "sub-mat",
      excel
    );
    expect(
      await screen.findByText(
        "Se registraron 4 notas (3 nuevas, 1 corregidas). 2 ya estaban iguales."
      )
    ).toBeInTheDocument();
  });

  test("un archivo con errores no registra nada y lista cada problema", async () => {
    const error = Object.assign(new Error("Solicitud no completada."), {
      payload: {
        errors: [
          {
            row: 9,
            student_code: "EST-2",
            unit: "Cuarta unidad",
            message: "La nota debe estar entre 0 y 100 (se recibió 120).",
          },
        ],
      },
    });
    evaluationServiceMock.importCourseWorkbook.mockRejectedValue(error);
    const user = userEvent.setup();
    renderPage();

    await user.upload(
      await screen.findByLabelText("Archivo de notas"),
      new File(["xlsx"], "notas.xlsx")
    );

    expect(
      await screen.findByText(
        /No se registró ninguna nota: el archivo tiene 1 problema/
      )
    ).toBeInTheDocument();
    const errorRow = screen.getByText(/se recibió 120/).closest("tr");
    expect(within(errorRow).getByText("9")).toBeInTheDocument();
    expect(within(errorRow).getByText("EST-2")).toBeInTheDocument();
    expect(within(errorRow).getByText("Cuarta unidad")).toBeInTheDocument();
  });

  test("quien no registra notas puede descargar pero no importar", async () => {
    renderPage(SHEET_ROUTE, sessionUser(["evaluation.configure_units"]));

    expect(
      await screen.findByRole("button", { name: "Descargar plantilla" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Importar Excel" })
    ).not.toBeInTheDocument();
  });
});
