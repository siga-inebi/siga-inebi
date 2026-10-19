import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

const cyclesServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  readiness: vi.fn(),
  activate: vi.fn(),
  defaults: vi.fn(),
  assignmentMatrix: vi.fn(),
  createAssignmentsBatch: vi.fn(),
  schedulePublication: vi.fn(),
  publishSchedule: vi.fn(),
  unpublishSchedule: vi.fn(),
  listNonComputableDays: vi.fn(),
  declareNonComputableDay: vi.fn(),
  removeNonComputableDay: vi.fn(),
}));
const teachersServiceMock = vi.hoisted(() => ({ listPage: vi.fn() }));
const enrolmentsServiceMock = vi.hoisted(() => ({
  listSectionOccupancy: vi.fn(),
}));

vi.mock("@cycles/cyclesService.js", async (importOriginal) => {
  const original = await importOriginal();
  return { ...original, cyclesService: cyclesServiceMock };
});
vi.mock("@academics/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});
vi.mock("@teachers/teachersService.js", () => ({
  teachersService: teachersServiceMock,
}));
vi.mock("@enrolments/enrolmentsService.js", () => ({
  enrolmentsService: enrolmentsServiceMock,
}));

import { CycleDetailPage } from "@cycles/CycleDetailPage.jsx";
import { paginated } from "./fixtures/academics.js";
import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";
import { selectOption } from "./helpers/selectOption.jsx";
import {
  academicsServiceMock,
  resetAcademicsServiceMock,
} from "./mocks/academicsService.js";

const ADMIN = sessionUser(["scope.assign"]);

const DRAFT = {
  public_id: "c-2027",
  year: 2027,
  name: "Ciclo 2027",
  description: "",
  starts_on: "2027-01-15",
  ends_on: "2027-10-29",
  status: "draft",
  grade_offerings: [],
  curriculum_plans: [],
  teaching_assignments: [],
  enrolments: { total: 0, active: 0, withdrawn: 0, completed: 0, cancelled: 0 },
};
const ACTIVE = {
  ...DRAFT,
  public_id: "c-2026",
  name: "Ciclo 2026",
  status: "active",
};

const GRADE = { public_id: "g-1", name: "Primero", sequence: 1 };
const LEVEL = {
  public_id: "l-1",
  name: "Básico",
  sequence: 1,
  grades: [GRADE],
};
const CAMPUS = { public_id: "campus-1", name: "Central" };
const SHIFT = { public_id: "s-1", name: "Matutina", campus: CAMPUS };
const SECTION = {
  public_id: "sec-a",
  name: "A",
  capacity: 30,
  is_active: true,
  academic_cycle_id: "c-2027",
  grade: GRADE,
  shift: SHIFT,
  default_classroom_id: null,
  default_classroom: null,
  capacity_warning: null,
};
const MATH = { public_id: "sub-mat", name: "Matemática", code: "MAT" };
const LANG = { public_id: "sub-len", name: "Lenguaje", code: "LEN" };
const BLOCK = {
  public_id: "b-1",
  number: 1,
  name: "Bloque 1",
  starts_on: "07:30:00",
  ends_on: "08:15:00",
};

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.search}</output>;
}

function renderDetail(route, user = ADMIN) {
  return renderWithSession(
    <Routes>
      <Route
        element={
          <>
            <CycleDetailPage />
            <LocationProbe />
          </>
        }
        path="/app/ciclos/:cycleId"
      />
    </Routes>,
    { user, route }
  );
}

const readiness = (overrides = {}) => ({
  activation: { ready: false, gaps: [] },
  revert: { allowed: true, blockers: [] },
  close: { ready: true, gaps: [] },
  active_cycle: null,
  ...overrides,
});

beforeEach(() => {
  vi.clearAllMocks();
  resetAcademicsServiceMock();
  cyclesServiceMock.get.mockResolvedValue(DRAFT);
  cyclesServiceMock.readiness.mockResolvedValue(readiness());
  cyclesServiceMock.schedulePublication.mockResolvedValue({
    academic_cycle_id: "c-2027",
    is_published: false,
    published_at: null,
  });
  cyclesServiceMock.listNonComputableDays.mockResolvedValue(paginated([]));
  academicsServiceMock.listLevels.mockResolvedValue(paginated([LEVEL]));
  academicsServiceMock.listCampuses.mockResolvedValue(paginated([CAMPUS]));
  academicsServiceMock.listCampusShifts.mockResolvedValue(paginated([SHIFT]));
  enrolmentsServiceMock.listSectionOccupancy.mockResolvedValue(paginated([]));
});

describe("detalle del ciclo: resumen y lista de verificación (C7, C9)", () => {
  test("cada faltante dice qué falta y lleva a la pestaña que lo resuelve", async () => {
    const user = userEvent.setup();
    cyclesServiceMock.readiness.mockResolvedValue(
      readiness({
        activation: {
          ready: false,
          gaps: [
            {
              code: "missing_curriculum_plan",
              message: "Falta plan de estudios para el grado 'Primero'.",
              grade: { public_id: "g-1", name: "Primero" },
              section: null,
              subject: null,
            },
            {
              code: "missing_teacher",
              message:
                "Falta asignar docente para 'Matemática' en la sección 'A'.",
              grade: { public_id: "g-1", name: "Primero" },
              section: null,
              subject: null,
            },
          ],
        },
      })
    );
    renderDetail("/app/ciclos/c-2027");

    expect(
      await screen.findByText("Falta para activar (2)")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Falta plan de estudios para el grado 'Primero'.")
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Ir a Plan de estudios" })
    );

    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent(
        "tab=plan&plan_grade_id=g-1"
      )
    );
    await waitFor(() =>
      expect(academicsServiceMock.listCurriculumPlans).toHaveBeenCalledWith(
        expect.objectContaining({
          academic_cycle_id: "c-2027",
          grade_id: "g-1",
        })
      )
    );
  });

  test("con otro ciclo activo, Activar se deshabilita y enlaza ese ciclo (D1)", async () => {
    cyclesServiceMock.readiness.mockResolvedValue(
      readiness({ active_cycle: { public_id: "c-2026", name: "Ciclo 2026" } })
    );
    renderDetail("/app/ciclos/c-2027");

    expect(
      await screen.findByRole("link", { name: "Ver «Ciclo 2026»" })
    ).toHaveAttribute("href", "/app/ciclos/c-2026");
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Activar" })).toBeDisabled()
    );
  });

  test("con la estructura completa avisa que se puede activar", async () => {
    cyclesServiceMock.readiness.mockResolvedValue(
      readiness({ activation: { ready: true, gaps: [] } })
    );
    renderDetail("/app/ciclos/c-2027");

    expect(
      await screen.findByText(/La estructura está completa/)
    ).toBeInTheDocument();
    expect(screen.getByText("Estructura registrada")).toBeInTheDocument();
  });

  test("un ciclo activo lista lo pendiente para cerrar", async () => {
    cyclesServiceMock.get.mockResolvedValue(ACTIVE);
    cyclesServiceMock.readiness.mockResolvedValue(
      readiness({
        close: {
          ready: false,
          gaps: [
            {
              code: "evaluation_unit_open",
              message: "La unidad U1 sigue abierta.",
            },
          ],
        },
      })
    );
    renderDetail("/app/ciclos/c-2026");

    expect(
      await screen.findByText("La unidad U1 sigue abierta.")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Ir a Evaluación" })
    ).toHaveAttribute("href", "/app/evaluacion");
  });
});

describe("pestaña Secciones (S1)", () => {
  test("crea una sección del ciclo en borrador", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listSections.mockResolvedValue(paginated([SECTION]));
    academicsServiceMock.createSection.mockResolvedValue(SECTION);
    renderDetail("/app/ciclos/c-2027?tab=secciones");

    expect(await screen.findByText("Matutina")).toBeInTheDocument();
    expect(academicsServiceMock.listSections).toHaveBeenCalledWith({
      page: 1,
      page_size: 25,
      academic_cycle_id: "c-2027",
    });

    await user.click(screen.getByRole("button", { name: "Nueva sección" }));
    const dialog = await screen.findByRole("dialog", { name: "Nueva sección" });
    await selectOption(user, /^Grado/, "Primero · Básico", dialog);
    await selectOption(user, /^Jornada/, "Matutina · Central", dialog);
    fireEvent.change(within(dialog).getByLabelText(/^Nombre/), {
      target: { value: "B" },
    });
    await user.click(
      within(dialog).getByRole("button", { name: "Crear sección" })
    );

    await waitFor(() =>
      expect(academicsServiceMock.createSection).toHaveBeenCalledWith({
        grade_id: "g-1",
        shift_id: "s-1",
        name: "B",
        capacity: 0,
        academic_cycle_id: "c-2027",
      })
    );
  });

  test("con el ciclo activo solo consulta y muestra la ocupación (S5)", async () => {
    cyclesServiceMock.get.mockResolvedValue(ACTIVE);
    academicsServiceMock.listSections.mockResolvedValue(
      paginated([{ ...SECTION, academic_cycle_id: "c-2026" }])
    );
    enrolmentsServiceMock.listSectionOccupancy.mockResolvedValue(
      paginated([
        {
          public_id: "sec-a",
          occupied_seats: 12,
          available_seats: 18,
          capacity: 30,
        },
      ])
    );
    renderDetail("/app/ciclos/c-2026?tab=secciones");

    expect(await screen.findByText("12 (18 libres)")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Nueva sección" })
    ).toBeDisabled();
    expect(
      screen.getByText(/la lista de secciones se consulta pero no se modifica/)
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Acciones de/ })
    ).not.toBeInTheDocument();
  });
});

describe("pestaña Plan de estudios (S2, N2)", () => {
  test("genera el plan desde los cursos del nivel con avance y rechazos por fila", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listCurriculumPlans.mockImplementation(
      async (params) =>
        params.page_size === 100
          ? paginated([{ public_id: "p-1", subject: LANG, grade: GRADE }])
          : paginated([])
    );
    academicsServiceMock.listLevelSubjects.mockResolvedValue(
      paginated([
        {
          public_id: "ls-1",
          subject: LANG,
          is_required: true,
          weekly_hours: 5,
        },
        {
          public_id: "ls-2",
          subject: MATH,
          is_required: true,
          weekly_hours: 5,
        },
        {
          public_id: "ls-3",
          subject: { public_id: "sub-art", name: "Artes" },
          is_required: false,
          weekly_hours: 2,
        },
      ])
    );
    academicsServiceMock.createCurriculumPlan.mockImplementation(
      async (payload) => {
        if (payload.subject_id === "sub-art") {
          throw new Error("El curso no está activo.");
        }
        return { public_id: "nuevo" };
      }
    );
    renderDetail("/app/ciclos/c-2027?tab=plan");

    expect(
      await screen.findByText(/«Cursos del nivel» \(en\s+Niveles\)/)
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Generar desde cursos del nivel" })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Generar desde cursos del nivel",
    });
    await selectOption(user, /^Grado/, "Primero · Básico", dialog);

    // Lenguaje ya está en el plan: solo se proponen los que faltan.
    expect(await within(dialog).findByText("Matemática")).toBeInTheDocument();
    expect(within(dialog).queryByText("Lenguaje")).not.toBeInTheDocument();

    await user.click(
      within(dialog).getByRole("button", { name: "Agregar 2 cursos" })
    );

    expect(
      await within(dialog).findByText("El curso no está activo.")
    ).toBeInTheDocument();
    expect(within(dialog).getByRole("status")).toHaveTextContent(
      "Agregados 1 de 2."
    );
    expect(academicsServiceMock.createCurriculumPlan).toHaveBeenCalledWith({
      academic_cycle_id: "c-2027",
      grade_id: "g-1",
      subject_id: "sub-mat",
      is_required: true,
    });
    expect(academicsServiceMock.createCurriculumPlan).toHaveBeenCalledWith(
      expect.objectContaining({ subject_id: "sub-art", is_required: false })
    );
  });
});

describe("pestaña Asignaciones (AD1, AD3)", () => {
  const ROW = {
    section: {
      public_id: "sec-a",
      name: "A",
      grade: { public_id: "g-1", name: "Primero" },
      shift: { public_id: "s-1", name: "Matutina" },
    },
    cells: [
      {
        subject: { public_id: "sub-len", name: "Lenguaje" },
        assignment: {
          public_id: "as-1",
          teacher: { public_id: "t-1", name: "Ana López" },
          starts_on: "2027-01-15",
        },
      },
      {
        subject: { public_id: "sub-mat", name: "Matemática" },
        assignment: null,
      },
    ],
  };

  test("marca lo que falta y asigna con un clic por celda", async () => {
    const user = userEvent.setup();
    cyclesServiceMock.assignmentMatrix.mockResolvedValue(paginated([ROW]));
    cyclesServiceMock.createAssignmentsBatch.mockResolvedValue({
      created: [{ public_id: "as-2" }],
      failed: [],
    });
    teachersServiceMock.listPage.mockResolvedValue(
      paginated([
        {
          public_id: "t-2",
          employee_code: "DOC-2",
          person: { first_name: "Luis", last_name: "Pérez" },
        },
      ])
    );
    renderDetail("/app/ciclos/c-2027?tab=asignaciones");

    expect(await screen.findByText("Lenguaje: Ana López")).toBeInTheDocument();
    expect(
      screen.getByText(/En esta página faltan 1 docente/)
    ).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Asignar Matemática en Primero A" })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Asignar docente",
    });
    await user.type(within(dialog).getByLabelText(/Docente/), "Lu");
    await user.click(await screen.findByText("Luis Pérez · DOC-2"));
    await user.click(within(dialog).getByRole("button", { name: "Asignar" }));

    await waitFor(() =>
      expect(cyclesServiceMock.createAssignmentsBatch).toHaveBeenCalledWith(
        "c-2027",
        {
          items: [
            { section_id: "sec-a", subject_id: "sub-mat", teacher_id: "t-2" },
          ],
        }
      )
    );
  });

  test("muestra el rechazo del backend sin cerrar la ventana", async () => {
    const user = userEvent.setup();
    cyclesServiceMock.assignmentMatrix.mockResolvedValue(paginated([ROW]));
    cyclesServiceMock.createAssignmentsBatch.mockResolvedValue({
      created: [],
      failed: [{ index: 0, detail: "El docente no está activo." }],
    });
    teachersServiceMock.listPage.mockResolvedValue(
      paginated([
        {
          public_id: "t-2",
          person: { first_name: "Luis", last_name: "Pérez" },
        },
      ])
    );
    renderDetail("/app/ciclos/c-2027?tab=asignaciones");

    await user.click(
      await screen.findByRole("button", {
        name: "Asignar Matemática en Primero A",
      })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Asignar docente",
    });
    await user.type(within(dialog).getByLabelText(/Docente/), "Lu");
    await user.click(await screen.findByText("Luis Pérez"));
    await user.click(within(dialog).getByRole("button", { name: "Asignar" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "El docente no está activo."
    );
  });
});

describe("pestaña Horarios (S3)", () => {
  test("muestra la reja semanal, la carga y publica el horario", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listSections.mockResolvedValue(paginated([SECTION]));
    academicsServiceMock.listScheduleBlocks.mockResolvedValue(
      paginated([BLOCK])
    );
    academicsServiceMock.listClassSessions.mockResolvedValue(
      paginated([
        {
          public_id: "cs-1",
          day_of_week: 1,
          subject: MATH,
          schedule_block: BLOCK,
          teacher: { public_id: "t-1", name: "Ana López" },
          classroom: null,
        },
      ])
    );
    academicsServiceMock.sectionWeeklyLoad.mockResolvedValue([
      {
        subject: MATH,
        declared_weekly_hours: 5,
        scheduled_periods: 1,
        matches: false,
      },
    ]);
    cyclesServiceMock.publishSchedule.mockResolvedValue({ is_published: true });
    renderDetail("/app/ciclos/c-2027?tab=horarios&hor_section=sec-a");

    const grid = await screen.findByRole("table", {
      name: "Horario de Primero A · Matutina",
    });
    expect(await within(grid).findByText("Ana López")).toBeInTheDocument();
    expect(
      within(grid).getByText("Bloque 1 · 07:30–08:15")
    ).toBeInTheDocument();
    expect(await screen.findByText("No coincide")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Publicar horario" }));
    await waitFor(() =>
      expect(cyclesServiceMock.publishSchedule).toHaveBeenCalledWith("c-2027")
    );
  });

  test("agrega una clase desde una celda vacía", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listSections.mockResolvedValue(paginated([SECTION]));
    academicsServiceMock.listScheduleBlocks.mockResolvedValue(
      paginated([BLOCK])
    );
    academicsServiceMock.listCurriculumPlans.mockResolvedValue(
      paginated([{ public_id: "p-1", subject: MATH, grade: GRADE }])
    );
    academicsServiceMock.createClassSession.mockResolvedValue({});
    renderDetail("/app/ciclos/c-2027?tab=horarios&hor_section=sec-a");

    await user.click(
      await screen.findByRole("button", {
        name: "Agregar clase el Martes en Bloque 1 · 07:30–08:15",
      })
    );
    const dialog = await screen.findByRole("dialog", { name: "Agregar clase" });
    await selectOption(user, /^Curso/, "Matemática", dialog);
    await user.click(
      within(dialog).getByRole("button", { name: "Agregar clase" })
    );

    await waitFor(() =>
      expect(academicsServiceMock.createClassSession).toHaveBeenCalledWith(
        "sec-a",
        {
          subject_id: "sub-mat",
          schedule_block_id: "b-1",
          day_of_week: 2,
        }
      )
    );
  });
});

describe("pestaña Días no computables (C8)", () => {
  test("lista, declara y quita días", async () => {
    const user = userEvent.setup();
    cyclesServiceMock.listNonComputableDays.mockResolvedValue(
      paginated([
        {
          public_id: "d-1",
          academic_cycle_id: "c-2027",
          day: "2027-09-15",
          reason: "Día de la Independencia",
        },
      ])
    );
    cyclesServiceMock.declareNonComputableDay.mockResolvedValue({});
    cyclesServiceMock.removeNonComputableDay.mockResolvedValue(null);
    renderDetail("/app/ciclos/c-2027?tab=dias");

    expect(
      await screen.findByText("Día de la Independencia")
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Declarar día" }));
    const dialog = await screen.findByRole("dialog", {
      name: "Declarar día no computable",
    });
    fireEvent.change(within(dialog).getByLabelText(/^Fecha/), {
      target: { value: "2027-06-25" },
    });
    fireEvent.change(within(dialog).getByLabelText(/^Motivo/), {
      target: { value: "Día del Maestro" },
    });
    await user.click(
      within(dialog).getByRole("button", { name: "Declarar día" })
    );
    await waitFor(() =>
      expect(cyclesServiceMock.declareNonComputableDay).toHaveBeenCalledWith(
        "c-2027",
        { day: "2027-06-25", reason: "Día del Maestro" }
      )
    );

    await user.click(screen.getByRole("button", { name: /^Quitar 15/ }));
    await user.click(screen.getByRole("button", { name: "Quitar día" }));
    await waitFor(() =>
      expect(cyclesServiceMock.removeNonComputableDay).toHaveBeenCalledWith(
        "d-1"
      )
    );
  });

  test("sin scope.assign solo consulta", async () => {
    renderDetail("/app/ciclos/c-2027?tab=dias", sessionUser([]));

    expect(
      await screen.findByText("Este ciclo no tiene días no computables.")
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Declarar día" })
    ).not.toBeInTheDocument();
  });
});
