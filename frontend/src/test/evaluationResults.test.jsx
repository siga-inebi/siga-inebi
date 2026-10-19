import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

const evaluationServiceMock = vi.hoisted(() => ({
  listUnits: vi.fn(),
  getReportCard: vi.fn(),
  getFinalSubjectGrade: vi.fn(),
  listFrozenResults: vi.fn(),
  getFrozenPromotion: vi.fn(),
  correctFrozenResult: vi.fn(),
  getResultTrace: vi.fn(),
  listSectionRecovery: vi.fn(),
  registerRecoveryGrade: vi.fn(),
  getGlobalConfig: vi.fn(),
  getCycleConfig: vi.fn(),
}));
const cyclesServiceMock = vi.hoisted(() => ({ list: vi.fn() }));
const studentsServiceMock = vi.hoisted(() => ({ listPage: vi.fn() }));
const enrolmentsServiceMock = vi.hoisted(() => ({ listHistory: vi.fn() }));

vi.mock("@evaluation/evaluationService.js", async (importOriginal) => {
  const original = await importOriginal();
  return { ...original, evaluationService: evaluationServiceMock };
});
vi.mock("@cycles/cyclesService.js", async (importOriginal) => {
  const original = await importOriginal();
  return { ...original, cyclesService: cyclesServiceMock };
});
vi.mock("@academics/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});
vi.mock("@students/studentsService.js", () => ({
  studentsService: studentsServiceMock,
}));
vi.mock("@enrolments/enrolmentsService.js", () => ({
  enrolmentsService: enrolmentsServiceMock,
}));

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

const DIRECTOR = sessionUser([
  "student.view_basic",
  "grade.write",
  "grade.correct",
  "audit.read",
]);
const ACTIVE = { public_id: "c-2026", name: "Ciclo 2026", status: "active" };
const CLOSED = { public_id: "c-2025", name: "Ciclo 2025", status: "closed" };
const UNITS = [
  { public_id: "u-1", number: 1, name: "Primera unidad", status: "closed" },
  { public_id: "u-2", number: 2, name: "Segunda unidad", status: "open" },
];
const MATH = { public_id: "sub-mat", name: "Matemática" };
const LANG = { public_id: "sub-len", name: "Lenguaje" };
const SECTION = {
  public_id: "sec-a",
  name: "A",
  grade: { public_id: "g-1", name: "Primero Básico" },
  shift: { public_id: "s-1", name: "Matutina" },
};
const enrolmentIn = (cycle) => ({
  public_id: `e-${cycle.public_id}`,
  status: cycle.status === "active" ? "active" : "completed",
  academic_cycle: { public_id: cycle.public_id, name: cycle.name },
  grade: { public_id: "g-1", name: "Primero Básico" },
  section: { public_id: "sec-a", name: "A", grade_name: "Primero Básico" },
  student: { public_id: "st-1", full_name: "Ana López", student_code: "EST-1" },
});

function renderPage(route, user = DIRECTOR) {
  return renderWithSession(<EvaluationPage />, { user, route });
}

beforeEach(() => {
  vi.clearAllMocks();
  resetAcademicsServiceMock();
  cyclesServiceMock.list.mockResolvedValue(paginated([ACTIVE, CLOSED]));
  evaluationServiceMock.listUnits.mockResolvedValue(paginated(UNITS));
  evaluationServiceMock.getGlobalConfig.mockResolvedValue({
    default_unit_count: 4,
  });
  evaluationServiceMock.getCycleConfig.mockResolvedValue(null);
  academicsServiceMock.listSections.mockResolvedValue(paginated([SECTION]));
  academicsServiceMock.listCurriculumPlans.mockResolvedValue(
    paginated([
      { public_id: "p-1", grade: SECTION.grade, subject: MATH },
      { public_id: "p-2", grade: SECTION.grade, subject: LANG },
    ])
  );
  enrolmentsServiceMock.listHistory.mockResolvedValue(
    paginated([enrolmentIn(CLOSED), enrolmentIn(ACTIVE)])
  );
  evaluationServiceMock.getReportCard.mockResolvedValue([
    {
      public_id: "gr-1",
      evaluation_unit_id: "u-1",
      subject_detail: MATH,
      value: 59,
    },
    {
      public_id: "gr-2",
      evaluation_unit_id: "u-2",
      subject_detail: MATH,
      value: 60,
    },
  ]);
});

describe("Recuperación por sección (V4)", () => {
  const ROW = {
    enrolment_id: "e-1",
    student: {
      public_id: "st-1",
      full_name: "Ana López",
      student_code: "EST-1",
    },
    eligible: true,
    reasons: [],
    attendance_percentage: 92,
    failed_count: 1,
    failed_limit: 3,
    recovery_already_used: false,
    failed_subjects: [
      { public_id: "sub-mat", name: "Matemática", final_grade: 55 },
    ],
  };
  const NOT_ELIGIBLE = {
    ...ROW,
    enrolment_id: "e-2",
    student: {
      public_id: "st-2",
      full_name: "Bruno Díaz",
      student_code: "EST-2",
    },
    eligible: false,
    reasons: ["La asistencia no alcanza el mínimo."],
    attendance_percentage: 60,
  };

  test("lista la elegibilidad de la sección y registra la recuperación", async () => {
    const user = userEvent.setup();
    evaluationServiceMock.listSectionRecovery.mockResolvedValue(
      paginated([ROW, NOT_ELIGIBLE])
    );
    evaluationServiceMock.registerRecoveryGrade.mockResolvedValue({});
    renderPage("/app/evaluacion?tab=recuperacion&seccion=sec-a");

    expect(await screen.findByText("Ana López")).toBeInTheDocument();
    expect(evaluationServiceMock.listSectionRecovery).toHaveBeenCalledWith(
      "c-2026",
      "sec-a",
      expect.objectContaining({ page: 1 })
    );
    expect(screen.getByText("Elegible")).toBeInTheDocument();
    expect(screen.getByText("No elegible")).toBeInTheDocument();
    expect(
      screen.getByText("La asistencia no alcanza el mínimo.")
    ).toBeInTheDocument();
    expect(screen.getAllByText("Matemática (55)")).toHaveLength(2);
    // Sin elegibilidad no hay nada que registrar.
    expect(
      screen.queryByRole("button", { name: "Acciones de Bruno Díaz" })
    ).toBeNull();

    await user.click(
      screen.getByRole("button", { name: "Acciones de Ana López" })
    );
    await user.click(
      screen.getByRole("menuitem", {
        name: "Registrar recuperación de Matemática",
      })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Registrar recuperación",
    });
    await user.type(
      within(dialog).getByLabelText(/Nota de recuperación/),
      "75"
    );
    await user.click(
      within(dialog).getByRole("button", { name: "Registrar recuperación" })
    );

    await waitFor(() =>
      expect(evaluationServiceMock.registerRecoveryGrade).toHaveBeenCalledWith(
        "c-2026",
        "e-1",
        { subject: "sub-mat", value: 75 }
      )
    );
  });

  test("sin grade.write solo consulta", async () => {
    evaluationServiceMock.listSectionRecovery.mockResolvedValue(
      paginated([ROW])
    );
    renderPage(
      "/app/evaluacion?tab=recuperacion&seccion=sec-a",
      sessionUser(["student.view_basic"])
    );

    expect(await screen.findByText("Ana López")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Acciones de Ana López" })
    ).toBeNull();
  });
});

describe("Resultados del estudiante (V5, V7)", () => {
  test("busca al estudiante en el servidor y muestra su boleta del ciclo", async () => {
    const user = userEvent.setup();
    studentsServiceMock.listPage.mockResolvedValue(
      paginated([
        {
          public_id: "st-1",
          student_code: "EST-1",
          person: { first_name: "Ana", last_name: "López" },
        },
      ])
    );
    evaluationServiceMock.getFinalSubjectGrade.mockImplementation(
      (_cycle, _enrolment, subject) =>
        Promise.resolve(
          subject === "sub-mat"
            ? {
                average: 59.5,
                final_grade: 60,
                graded_units: 2,
                total_units: 2,
                pending_units: 0,
                condition: "approved",
              }
            : {
                average: null,
                final_grade: null,
                graded_units: 0,
                total_units: 2,
                pending_units: 2,
                condition: null,
              }
        )
    );
    renderPage("/app/evaluacion?tab=resultados");

    await user.type(
      await screen.findByRole("combobox", { name: /Estudiante/ }),
      "Ana"
    );
    await user.click(
      await screen.findByRole("option", { name: "Ana López · EST-1" })
    );

    expect(await screen.findByText("Boleta de Ana López")).toBeInTheDocument();
    expect(studentsServiceMock.listPage).toHaveBeenCalledWith({
      search: "Ana",
    });
    expect(enrolmentsServiceMock.listHistory).toHaveBeenCalledWith(
      expect.objectContaining({ student_id: "st-1" })
    );
    // La matrícula del ciclo elegido, no la del ciclo cerrado.
    await waitFor(() =>
      expect(evaluationServiceMock.getReportCard).toHaveBeenCalledWith(
        "c-2026",
        "e-c-2026"
      )
    );
    const mathRow = (await screen.findByText("Matemática")).closest("tr");
    expect(within(mathRow).getByText("59")).toBeInTheDocument();
    // INC-008: se muestra final_grade de la API, sin recalcular el promedio.
    expect(
      await within(mathRow).findByText("60", { selector: "span" })
    ).toBeInTheDocument();
    expect(within(mathRow).getByText("Aprobada")).toBeInTheDocument();
    const langRow = screen.getByText("Lenguaje").closest("tr");
    await waitFor(() =>
      expect(within(langRow).getAllByText("Sin calificar")).toHaveLength(2)
    );
    // Ciclo abierto: no hay corrección de resultado congelado.
    await userEvent.click(
      within(mathRow).getByRole("button", { name: "Acciones de Matemática" })
    );
    expect(screen.queryByRole("menuitem", { name: "Corregir" })).toBeNull();
    expect(evaluationServiceMock.listFrozenResults).not.toHaveBeenCalled();
  });

  test("avisa si el estudiante no tiene matrícula en el ciclo", async () => {
    enrolmentsServiceMock.listHistory.mockResolvedValue(
      paginated([enrolmentIn(CLOSED)])
    );
    renderPage("/app/evaluacion?tab=resultados&estudiante=st-1");

    expect(
      await screen.findByText(/no tiene matrícula en «Ciclo 2026»/)
    ).toBeInTheDocument();
  });

  test("ciclo cerrado: resultados congelados, promoción, corrección y trazabilidad", async () => {
    const user = userEvent.setup();
    evaluationServiceMock.listFrozenResults.mockResolvedValue([
      {
        public_id: "fr-1",
        enrolment_id: "e-c-2025",
        subject_id: "sub-mat",
        subject_name: "Matemática",
        final_grade: 55,
        condition: "failed",
        recovery_grade: null,
        is_correction: false,
        correction_reason: "",
      },
    ]);
    evaluationServiceMock.getFrozenPromotion.mockResolvedValue({
      promoted: false,
      condition: "not_promoted",
      failed_subjects: ["Matemática"],
      is_correction: false,
      correction_reason: "",
    });
    evaluationServiceMock.correctFrozenResult.mockResolvedValue({});
    evaluationServiceMock.getResultTrace.mockResolvedValue({
      enrolment_id: "e-c-2025",
      subject_id: "sub-mat",
      unit_grades: [{ unit_number: 1, unit_name: "Primera unidad", value: 59 }],
      recovery_grade: null,
      corrections: [
        {
          stage: "live",
          unit_number: 1,
          previous_value: 50,
          new_value: 59,
          reason: "",
          corrected_by: "rosa.perez",
          corrected_at: "2025-09-10T15:00:00Z",
        },
      ],
    });
    renderPage("/app/evaluacion?ciclo=c-2025&tab=resultados&estudiante=st-1");

    expect(
      await screen.findByText(
        /No promovido: 1 subáreas sin aprobar \(Matemática\)/
      )
    ).toBeInTheDocument();
    const mathRow = (await screen.findByText("Matemática")).closest("tr");
    expect(await within(mathRow).findByText("55")).toBeInTheDocument();
    expect(within(mathRow).getByText("Reprobada")).toBeInTheDocument();
    expect(evaluationServiceMock.getFinalSubjectGrade).not.toHaveBeenCalled();

    await user.click(
      within(mathRow).getByRole("button", { name: "Acciones de Matemática" })
    );
    await user.click(screen.getByRole("menuitem", { name: "Corregir" }));
    const dialog = await screen.findByRole("dialog", {
      name: "Corregir resultado congelado",
    });
    const grade = within(dialog).getByLabelText(/Nota final corregida/);
    await user.clear(grade);
    await user.type(grade, "61");
    await user.type(
      within(dialog).getByLabelText(/Motivo de la corrección/),
      "Error de transcripción"
    );
    await user.click(
      within(dialog).getByRole("button", { name: "Corregir resultado" })
    );
    await waitFor(() =>
      expect(evaluationServiceMock.correctFrozenResult).toHaveBeenCalledWith(
        "c-2025",
        "e-c-2025",
        "sub-mat",
        { final_grade: 61, reason: "Error de transcripción" }
      )
    );

    await user.click(
      within(mathRow).getByRole("button", { name: "Acciones de Matemática" })
    );
    await user.click(
      screen.getByRole("menuitem", { name: "Ver trazabilidad" })
    );
    const trace = await screen.findByRole("dialog", {
      name: "Trazabilidad de Matemática",
    });
    expect(
      await within(trace).findByText(/1\. Primera unidad: 59/)
    ).toBeInTheDocument();
    expect(within(trace).getByText(/50 → 59/)).toBeInTheDocument();
    expect(evaluationServiceMock.getResultTrace).toHaveBeenCalledWith(
      "e-c-2025",
      "sub-mat"
    );
  });

  test("sin grade.correct ni audit.read no hay acciones", async () => {
    evaluationServiceMock.listFrozenResults.mockResolvedValue([]);
    evaluationServiceMock.getFrozenPromotion.mockResolvedValue({
      promoted: true,
      failed_subjects: [],
      is_correction: false,
    });
    renderPage(
      "/app/evaluacion?ciclo=c-2025&tab=resultados&estudiante=st-1",
      sessionUser(["student.view_basic"])
    );

    expect(await screen.findByText(/^Promovido/)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Acciones de Matemática" })
    ).toBeNull();
  });
});
