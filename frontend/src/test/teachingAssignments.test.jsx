import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

const { cyclesServiceMock, teachersServiceMock } = vi.hoisted(() => ({
  cyclesServiceMock: {
    list: vi.fn(),
    cloneAssignmentsPreview: vi.fn(),
    createAssignmentsBatch: vi.fn(),
  },
  teachersServiceMock: {
    list: vi.fn(),
    listPage: vi.fn(),
    nextCode: vi.fn(),
  },
}));

vi.mock("@cycles/cyclesService.js", async () => {
  const actual = await vi.importActual("@cycles/cyclesService.js");
  return { ...actual, cyclesService: cyclesServiceMock };
});
vi.mock("@teachers/teachersService.js", () => ({
  teachersService: teachersServiceMock,
}));
vi.mock("@academics/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});

import { BulkAssignmentWindow } from "@academics/BulkAssignmentWindow.jsx";
import { CloneAssignmentsWindow } from "@academics/CloneAssignmentsWindow.jsx";
import { TeachingAssignmentsPage } from "@academics/TeachingAssignmentsPage.jsx";
import { DocentesPage } from "@teachers/DocentesPage.jsx";
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

const CYCLE_2026 = {
  public_id: "cycle-2026",
  year: 2026,
  name: "Ciclo 2026",
  status: "active",
  starts_on: "2026-01-15",
  ends_on: "2026-10-31",
};
const CYCLE_2027 = {
  ...CYCLE_2026,
  public_id: "cycle-2027",
  year: 2027,
  name: "Ciclo 2027",
  status: "draft",
  starts_on: "2027-01-15",
};

const ASSIGNMENT = {
  public_id: "assign-1",
  academic_cycle_id: "cycle-2026",
  section_id: "section-a",
  subject_id: "subject-mat",
  teacher_id: "teacher-1",
  section: { public_id: "section-a", name: "A", grade_name: "Primero" },
  subject: { public_id: "subject-mat", name: "Matemática", code: "MAT" },
  teacher: { public_id: "teacher-1", name: "Ana López" },
  starts_on: "2026-01-20",
  ends_on: null,
};

const TEACHER_ROW = {
  id: 7,
  public_id: "teacher-2",
  employee_code: "EMP-2",
  person: { first_name: "Bruno", last_name: "Pérez" },
};

const MANAGER = sessionUser(["scope.assign"]);

beforeEach(() => {
  vi.clearAllMocks();
  resetAcademicsServiceMock();
  cyclesServiceMock.list.mockResolvedValue(paginated([CYCLE_2027, CYCLE_2026]));
  teachersServiceMock.listPage.mockResolvedValue(paginated([TEACHER_ROW]));
  academicsServiceMock.listTeachingAssignments.mockResolvedValue(
    paginated([ASSIGNMENT])
  );
});

async function pickRemote(user, label, text, option, scope = screen) {
  await user.type(await scope.findByRole("combobox", { name: label }), text);
  await user.click(await screen.findByRole("option", { name: option }));
}

describe("Asignaciones docentes: listado en el servidor (AD2)", () => {
  test("muestra los nombres que trae el listado, sin descargar catálogos", async () => {
    renderWithSession(<TeachingAssignmentsPage />, {
      user: MANAGER,
      route: "/app/asignaciones",
    });

    expect(await screen.findByText("Primero A")).toBeInTheDocument();
    expect(screen.getByText("Matemática (MAT)")).toBeInTheDocument();
    expect(screen.getByText("Ana López")).toBeInTheDocument();
    expect(screen.getByText("Vigente")).toBeInTheDocument();
    expect(academicsServiceMock.listSections).not.toHaveBeenCalled();
    expect(academicsServiceMock.listSubjects).not.toHaveBeenCalled();
    expect(teachersServiceMock.listPage).not.toHaveBeenCalled();
  });

  test("lee los filtros de la URL y los manda al servidor", async () => {
    renderWithSession(<TeachingAssignmentsPage />, {
      user: MANAGER,
      route: "/app/asignaciones?academic_cycle_id=cycle-2026&current=true",
    });

    await screen.findByText("Primero A");
    expect(academicsServiceMock.listTeachingAssignments).toHaveBeenCalledWith({
      page: 1,
      page_size: 25,
      academic_cycle_id: "cycle-2026",
      current: "true",
    });
    expect(screen.getByLabelText("Solo vigentes")).toBeChecked();
  });

  test("Solo vigentes y el docente filtran en el servidor", async () => {
    const user = userEvent.setup();
    renderWithSession(<TeachingAssignmentsPage />, {
      user: MANAGER,
      route: "/app/asignaciones",
    });
    await screen.findByText("Primero A");

    await user.click(screen.getByLabelText("Solo vigentes"));
    await waitFor(() =>
      expect(
        academicsServiceMock.listTeachingAssignments
      ).toHaveBeenLastCalledWith({ page: 1, page_size: 25, current: "true" })
    );

    await pickRemote(user, /Docente/, "Bru", "Bruno Pérez · EMP-2");
    await waitFor(() =>
      expect(
        academicsServiceMock.listTeachingAssignments
      ).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 25,
        current: "true",
        teacher_id: "teacher-2",
      })
    );
    expect(teachersServiceMock.listPage).toHaveBeenCalledWith({
      search: "Bru",
    });
  });

  test("sin scope.assign no ofrece altas ni reasignar", async () => {
    renderWithSession(<TeachingAssignmentsPage />, {
      user: sessionUser([]),
      route: "/app/asignaciones",
    });
    await screen.findByText("Primero A");

    expect(
      screen.queryByRole("button", { name: "Nueva asignación" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Asignar por lotes" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Reasignar a otro docente" })
    ).not.toBeInTheDocument();
  });

  test("reasignar elige el docente entrante con búsqueda", async () => {
    const user = userEvent.setup();
    renderWithSession(<TeachingAssignmentsPage />, {
      user: MANAGER,
      route: "/app/asignaciones",
    });
    await user.click(
      await screen.findByRole("button", { name: "Reasignar a otro docente" })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Reasignar curso",
    });
    await pickRemote(
      user,
      /Docente entrante/,
      "Bru",
      "Bruno Pérez · EMP-2",
      within(dialog)
    );
    await user.type(
      within(dialog).getByLabelText(/Último día del docente saliente/),
      "2026-06-30"
    );
    await user.click(within(dialog).getByRole("button", { name: "Reasignar" }));

    await waitFor(() =>
      expect(
        academicsServiceMock.reassignTeachingAssignment
      ).toHaveBeenCalledWith("assign-1", {
        teacher_id: "teacher-2",
        ends_on: "2026-06-30",
      })
    );
  });
});

describe("Asignar por lotes (AD2)", () => {
  test("ofrece solo los cursos del plan del grado y envía un lote", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listSections.mockResolvedValue(
      paginated([
        {
          public_id: "section-a",
          name: "A",
          grade: { public_id: "grade-1", name: "Primero" },
          shift: { public_id: "shift-m", name: "Matutina" },
        },
      ])
    );
    academicsServiceMock.listCurriculumPlans.mockResolvedValue(
      paginated([
        { public_id: "plan-1", subject: ASSIGNMENT.subject },
        {
          public_id: "plan-2",
          subject: {
            public_id: "subject-com",
            name: "Comunicación",
            code: "COM",
          },
        },
      ])
    );
    cyclesServiceMock.createAssignmentsBatch.mockResolvedValue({
      created: [],
      failed: [
        {
          index: 0,
          section_id: "section-a",
          subject_id: "subject-com",
          teacher_id: "teacher-2",
          detail: "El docente ya tiene otra clase en ese bloque.",
        },
      ],
    });

    renderWithSession(<BulkAssignmentWindow onClose={vi.fn()} />, {
      user: MANAGER,
    });
    const dialog = await screen.findByRole("dialog", {
      name: "Asignación docente por lotes",
    });

    await selectOption(user, /Ciclo escolar/, "Ciclo 2026 · Activo", dialog);
    await pickRemote(
      user,
      /Sección/,
      "Pri",
      "Primero A · Matutina",
      within(dialog)
    );
    await user.type(
      within(dialog).getByLabelText(/Vigente desde/),
      "2026-03-02"
    );

    expect(
      await within(dialog).findByText("Comunicación (COM)")
    ).toBeInTheDocument();
    expect(academicsServiceMock.listCurriculumPlans).toHaveBeenCalledWith({
      academic_cycle_id: "cycle-2026",
      grade_id: "grade-1",
      page_size: 100,
    });
    expect(academicsServiceMock.listTeachingAssignments).toHaveBeenCalledWith({
      section_id: "section-a",
      current: true,
      page_size: 100,
    });
    // Matemática ya tiene docente vigente: no se ofrece de nuevo.
    expect(within(dialog).getByText("Ana López")).toBeInTheDocument();

    await pickRemote(
      user,
      /Docente para Comunicación/,
      "Bru",
      "Bruno Pérez · EMP-2",
      within(dialog)
    );
    await user.click(
      within(dialog).getByRole("button", { name: /Asignar 1 curso/ })
    );

    await waitFor(() =>
      expect(cyclesServiceMock.createAssignmentsBatch).toHaveBeenCalledWith(
        "cycle-2026",
        {
          starts_on: "2026-03-02",
          items: [
            {
              section_id: "section-a",
              subject_id: "subject-com",
              teacher_id: "teacher-2",
            },
          ],
        }
      )
    );
    expect(
      await within(dialog).findByText(
        /Comunicación \(COM\): El docente ya tiene otra clase/
      )
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText("0 asignaciones creadas.")
    ).toBeInTheDocument();
  });
});

describe("Clonar asignaciones con vista previa del servidor (AD2)", () => {
  test("muestra la propuesta y envía solo las pendientes", async () => {
    const user = userEvent.setup();
    const target = {
      public_id: "section-a-2027",
      name: "A",
      grade_name: "Primero",
    };
    cyclesServiceMock.cloneAssignmentsPreview.mockResolvedValue({
      source_cycle: { public_id: "cycle-2026", name: "Ciclo 2026" },
      target_cycle: { public_id: "cycle-2027", name: "Ciclo 2027" },
      suggested_starts_on: "2027-01-15",
      summary: { total: 3, pending: 1, already_assigned: 1, unmatched: 1 },
      results: [
        {
          source_assignment_id: "src-1",
          section: ASSIGNMENT.section,
          subject: ASSIGNMENT.subject,
          teacher: ASSIGNMENT.teacher,
          target_section: target,
          status: "pending",
        },
        {
          source_assignment_id: "src-2",
          section: ASSIGNMENT.section,
          subject: { public_id: "subject-com", name: "Comunicación" },
          teacher: ASSIGNMENT.teacher,
          target_section: target,
          status: "already_assigned",
        },
        {
          source_assignment_id: "src-3",
          section: { public_id: "section-b", name: "B", grade_name: "Primero" },
          subject: ASSIGNMENT.subject,
          teacher: ASSIGNMENT.teacher,
          target_section: null,
          status: "unmatched",
        },
      ],
    });
    cyclesServiceMock.createAssignmentsBatch.mockResolvedValue({
      created: [
        {
          ...ASSIGNMENT,
          public_id: "new-1",
          section_id: "section-a-2027",
          subject_id: "subject-mat",
        },
      ],
      failed: [],
    });
    const onCreated = vi.fn();

    renderWithSession(
      <CloneAssignmentsWindow onClose={vi.fn()} onCreated={onCreated} />,
      { user: MANAGER }
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Clonar asignaciones en un ciclo nuevo",
    });
    await selectOption(user, /Copiar desde/, "Ciclo 2026 · Activo", dialog);
    await selectOption(user, /Copiar hacia/, "Ciclo 2027 · Borrador", dialog);

    expect(await within(dialog).findByText("Pendiente")).toBeInTheDocument();
    expect(within(dialog).getByText("Ya asignada")).toBeInTheDocument();
    expect(
      within(dialog).getAllByText(/Sin sección equivalente/).length
    ).toBeGreaterThan(0);
    expect(cyclesServiceMock.cloneAssignmentsPreview).toHaveBeenCalledWith(
      "cycle-2027",
      "cycle-2026"
    );
    // La fecha sugerida por el backend queda propuesta.
    expect(within(dialog).getByLabelText(/Vigente desde/)).toHaveValue(
      "2027-01-15"
    );

    await user.click(
      within(dialog).getByRole("button", { name: /Clonar 1 asignación/ })
    );
    await waitFor(() =>
      expect(cyclesServiceMock.createAssignmentsBatch).toHaveBeenCalledWith(
        "cycle-2027",
        {
          starts_on: "2027-01-15",
          items: [
            {
              section_id: "section-a-2027",
              subject_id: "subject-mat",
              teacher_id: "teacher-1",
            },
          ],
        }
      )
    );
    expect(
      await within(dialog).findByText("1 asignación creada.")
    ).toBeInTheDocument();
    expect(onCreated).toHaveBeenCalled();
    expect(
      academicsServiceMock.listTeachingAssignmentHistory
    ).not.toHaveBeenCalled();
  });
});

describe("Ficha del docente: qué imparte (AD4)", () => {
  const TEACHER = {
    id: 7,
    public_id: "teacher-1",
    employee_code: "EMP-1",
    specialty: "Matemática",
    position: "Docente Titulado",
    person: {
      public_id: "person-1",
      first_name: "Ana",
      last_name: "López",
      email: "ana@example.test",
      phone_number: "5555-0000",
    },
  };

  test("lista las asignaciones vigentes del docente", async () => {
    const user = userEvent.setup();
    teachersServiceMock.listPage.mockResolvedValue(paginated([TEACHER]));
    renderWithSession(<DocentesPage />, { user: MANAGER });

    await user.click(
      await screen.findByRole("button", { name: /Ver detalle de Ana López/ })
    );

    const dialog = await screen.findByRole("dialog");
    const table = await within(dialog).findByRole("table", {
      name: "Asignaciones vigentes",
    });
    const [header, first] = within(table).getAllByRole("row");
    expect(within(header).getByText("Sección")).toBeInTheDocument();
    expect(within(first).getByText("Primero A")).toBeInTheDocument();
    expect(within(first).getByText("Matemática")).toBeInTheDocument();
    expect(academicsServiceMock.listTeachingAssignments).toHaveBeenCalledWith({
      teacher_id: "teacher-1",
      current: true,
    });
  });

  test("sin scope.assign no consulta las asignaciones", async () => {
    const user = userEvent.setup();
    teachersServiceMock.listPage.mockResolvedValue(paginated([TEACHER]));
    renderWithSession(<DocentesPage />, { user: sessionUser([]) });

    await user.click(
      await screen.findByRole("button", { name: /Ver detalle de Ana López/ })
    );
    await screen.findByRole("dialog");

    expect(screen.queryByText("Qué imparte")).not.toBeInTheDocument();
    expect(academicsServiceMock.listTeachingAssignments).not.toHaveBeenCalled();
  });
});
