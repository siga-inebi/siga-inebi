import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

const teachersServiceMock = vi.hoisted(() => ({
  listPage: vi.fn(),
  list: vi.fn(),
  get: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
}));

const studentsServiceMock = vi.hoisted(() => ({
  listPage: vi.fn(),
}));

const cyclesServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  create: vi.fn(),
  activate: vi.fn(),
  clone: vi.fn(),
  defaults: vi.fn(),
}));

const enrolmentsServiceMock = vi.hoisted(() => ({
  getPromotion: vi.fn(),
  listActive: vi.fn(),
  listHistory: vi.fn(),
  listMovements: vi.fn(),
  create: vi.fn(),
  register: vi.fn(),
  matriculate: vi.fn(),
  reenrol: vi.fn(),
  listInitialCandidates: vi.fn(),
  bulkMatriculate: vi.fn(),
  listSectionOccupancy: vi.fn(),
  listDocuments: vi.fn(),
  addDocument: vi.fn(),
}));

const documentsServiceMock = vi.hoisted(() => ({
  listTypes: vi.fn(),
  createType: vi.fn(),
  updateType: vi.fn(),
  deactivateType: vi.fn(),
  listTemplates: vi.fn(),
  listTemplateIssuanceUses: vi.fn(),
  getTemplate: vi.fn(),
  createTemplate: vi.fn(),
  updateTemplate: vi.fn(),
  deactivateTemplate: vi.fn(),
  listTemplateVersions: vi.fn(),
  listFieldTags: vi.fn(),
  listEnrolmentRecords: vi.fn(),
  previewTemplate: vi.fn(),
  uploadRecord: vi.fn(),
  issuanceEligibility: vi.fn(),
}));

const reportingServiceMock = vi.hoisted(() => ({
  listAlerts: vi.fn(),
  acknowledge: vi.fn(),
  evaluate: vi.fn(),
  listAbsenceThresholds: vi.fn(),
  createAbsenceThreshold: vi.fn(),
}));

vi.mock("@cycles/cyclesService.js", async () => {
  const actual = await vi.importActual("@cycles/cyclesService.js");
  return { ...actual, cyclesService: cyclesServiceMock };
});

vi.mock("@enrolments/enrolmentsService.js", async () => {
  const actual = await vi.importActual("@enrolments/enrolmentsService.js");
  return { ...actual, enrolmentsService: enrolmentsServiceMock };
});

vi.mock("@documents/documentsService.js", async () => {
  const actual = await vi.importActual("@documents/documentsService.js");
  return { ...actual, documentsService: documentsServiceMock };
});

vi.mock("@reporting/reportingService.js", async () => {
  const actual = await vi.importActual("@reporting/reportingService.js");
  return { ...actual, reportingService: reportingServiceMock };
});

vi.mock("@teachers/teachersService.js", async () => {
  const actual = await vi.importActual("@teachers/teachersService.js");
  return { ...actual, teachersService: teachersServiceMock };
});

vi.mock("@students/studentsService.js", async () => {
  const actual = await vi.importActual("@students/studentsService.js");
  return { ...actual, studentsService: studentsServiceMock };
});

vi.mock("@academics/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});

import { AlertsPage } from "@reporting/AlertsPage.jsx";
import { AttendancePage } from "@attendance/AttendancePage.jsx";
import { EnrolmentsPage } from "@enrolments/EnrolmentsPage.jsx";
import { DocumentTypesPage } from "@documents/DocumentTypesPage.jsx";
import { TemplatesPage } from "@documents/TemplatesPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import { selectOption } from "./helpers/selectOption.jsx";
import {
  academicsServiceMock,
  resetAcademicsServiceMock,
} from "./mocks/academicsService.js";

const paged = (results) => ({ count: results.length, results });

const CYCLE = {
  public_id: "cycle-2026",
  year: 2026,
  name: "Ciclo 2026",
  description: "",
  starts_on: "2026-01-15",
  ends_on: "2026-10-30",
  status: "active",
};

const DRAFT_CYCLE = {
  ...CYCLE,
  public_id: "cycle-2027",
  year: 2027,
  name: "Ciclo 2027",
  status: "draft",
};

const ENROLMENT = {
  student: {
    public_id: "student-1",
    full_name: "Luis Perez",
    student_code: "EST-1",
  },
  academic_cycle: { public_id: "cycle-2026", name: "Ciclo 2026" },
  grade: { public_id: "grade-1", name: "Primero Basico" },
  section: {
    public_id: "section-a",
    name: "A",
    grade_name: "Primero Basico",
    shift_name: "Matutina",
  },
  public_id: "enr-1",
  student_id: "student-1",
  academic_cycle_id: "cycle-2026",
  grade_id: "grade-1",
  section_id: "section-a",
  effective_on: "2026-01-20",
  ends_on: null,
  status: "active",
  is_active: true,
};

const DOCUMENT_TYPES = [
  {
    public_id: "kind-1",
    code: "certificate",
    label: "Constancia",
    description: "",
    is_active: true,
  },
  {
    public_id: "kind-2",
    code: "report",
    label: "Reporte",
    description: "",
    is_active: true,
  },
];

const TEMPLATE = {
  public_id: "tpl-1",
  name: "Constancia de inscripcion",
  code: "CONST-INS",
  kind: "certificate",
  description: "",
  is_active: true,
  header: { institution: "INEBI" },
};

const ALERT = {
  public_id: "alert-1",
  alert_type: "frecuencia_ausencias",
  student_id: "student-1",
  student_name: "Luis Perez",
  student_code: "EST-1",
  shift_id: "shift-1",
  section_id: "section-a",
  event_date: "2026-08-06",
  is_active: true,
  acknowledged_at: null,
  acknowledged_by_username: "",
  created_at: "2026-08-06T12:00:00Z",
};

const STUDENT = {
  id: 1,
  public_id: "student-1",
  person: { first_name: "Luis", last_name: "Perez" },
  student_code: "EST-1",
};

const LEVEL = {
  public_id: "level-1",
  name: "Basico",
  code: "BAS",
  sequence: 3,
};

const GRADE = {
  public_id: "grade-1",
  name: "Primero Basico",
  code: "B1",
  sequence: 1,
  level: LEVEL,
};

const CAMPUS = {
  public_id: "campus-1",
  name: "Sede Central",
  code: "CENTRAL",
  is_main: true,
};

const SHIFT = {
  public_id: "shift-1",
  name: "Matutina",
  code: "MOR",
  campus: CAMPUS,
};

const SECTION = {
  public_id: "section-a",
  name: "A",
  academic_cycle_id: "cycle-2026",
  grade: {
    public_id: "grade-1",
    name: "Primero Basico",
    code: "B1",
    sequence: 1,
  },
  shift: { public_id: "shift-1", name: "Matutina", code: "MOR" },
};

const SUBJECT = {
  public_id: "subject-mat",
  name: "Matematica",
  code: "MAT",
  is_active: true,
};

const TEACHER = {
  id: 1,
  public_id: "teacher-1",
  person: { first_name: "Ana", last_name: "Lopez" },
  employee_code: "EMP-1",
};

const ASSIGNMENT = {
  public_id: "asg-1",
  academic_cycle_id: "cycle-2026",
  section_id: "section-a",
  subject_id: "subject-mat",
  teacher_id: "teacher-1",
  starts_on: "2026-01-20",
  ends_on: null,
};

describe("pantallas de los modulos con backend previo", () => {
  beforeEach(() => {
    resetAcademicsServiceMock();

    teachersServiceMock.listPage
      .mockReset()
      .mockResolvedValue(paged([TEACHER]));
    studentsServiceMock.listPage.mockReset().mockResolvedValue(paged([]));

    cyclesServiceMock.list
      .mockReset()
      .mockResolvedValue(paged([CYCLE, DRAFT_CYCLE]));
    cyclesServiceMock.get.mockReset().mockResolvedValue({
      ...CYCLE,
      grade_offerings: [],
      curriculum_plans: [],
      teaching_assignments: [],
    });
    cyclesServiceMock.activate.mockReset().mockResolvedValue(CYCLE);
    cyclesServiceMock.create.mockReset().mockResolvedValue(DRAFT_CYCLE);
    // El backend es el unico dueno de la regla del calendario; el formulario la
    // consulta por anio.
    cyclesServiceMock.defaults.mockReset().mockImplementation((year) =>
      Promise.resolve({
        year: Number(year),
        name: `Ciclo ${year}`,
        starts_on: `${year}-01-15`,
        ends_on: `${year}-10-29`,
      })
    );

    enrolmentsServiceMock.listActive
      .mockReset()
      .mockResolvedValue(paged([ENROLMENT]));
    enrolmentsServiceMock.listHistory
      .mockReset()
      .mockResolvedValue(paged([ENROLMENT]));
    enrolmentsServiceMock.listMovements
      .mockReset()
      .mockResolvedValue(paged([]));
    enrolmentsServiceMock.listDocuments
      .mockReset()
      .mockResolvedValue(paged([]));
    documentsServiceMock.issuanceEligibility
      .mockReset()
      .mockResolvedValue({ eligible: true, blocking_document_codes: [] });

    documentsServiceMock.listTypes
      .mockReset()
      .mockResolvedValue(paged(DOCUMENT_TYPES));
    documentsServiceMock.createType.mockReset().mockResolvedValue({});
    documentsServiceMock.updateType.mockReset().mockResolvedValue({});
    documentsServiceMock.deactivateType.mockReset().mockResolvedValue({});
    documentsServiceMock.listTemplates
      .mockReset()
      .mockResolvedValue(paged([TEMPLATE]));
    documentsServiceMock.listTemplateVersions
      .mockReset()
      .mockResolvedValue(paged([]));
    documentsServiceMock.listFieldTags.mockReset().mockResolvedValue(paged([]));
    documentsServiceMock.listEnrolmentRecords
      .mockReset()
      .mockResolvedValue(paged([]));
    documentsServiceMock.previewTemplate.mockReset().mockResolvedValue({
      content: "",
      markers: [],
      marker_count: 0,
    });
    documentsServiceMock.uploadRecord.mockReset().mockResolvedValue({});

    reportingServiceMock.listAlerts
      .mockReset()
      .mockResolvedValue(paged([ALERT]));
    reportingServiceMock.acknowledge
      .mockReset()
      .mockResolvedValue({ ...ALERT, acknowledged_at: "2026-08-06T13:00:00Z" });
    reportingServiceMock.listAbsenceThresholds
      .mockReset()
      .mockResolvedValue(paged([]));

    academicsServiceMock.listTeachingAssignmentHistory.mockResolvedValue(
      paged([ASSIGNMENT])
    );
  });

  describe("EnrolmentsPage", () => {
    async function selectStudentFilter(user) {
      const field = screen.getByRole("combobox", { name: "Estudiante" });
      await user.click(field);
      // Compatible con la búsqueda remota que introduce el PR #636.
      if (field.tagName === "INPUT") await user.type(field, "Luis");
      await user.click(
        await screen.findByRole("option", { name: "Luis Perez · EST-1" })
      );
    }
    beforeEach(() => {
      enrolmentsServiceMock.listSectionOccupancy.mockReset().mockResolvedValue({
        count: 1,
        results: [
          {
            public_id: "section-a",
            academic_cycle_id: "cycle-2026",
            capacity: 30,
            occupied_seats: 12,
            available_seats: 18,
          },
        ],
      });
      studentsServiceMock.listPage.mockResolvedValue(paged([STUDENT]));
      academicsServiceMock.listSections.mockResolvedValue(paged([SECTION]));
      // El catalogo de grados pide niveles con ?expand=grades, no un
      // /levels/{id}/grades/ por nivel: el mock ya trae el grado anidado.
      academicsServiceMock.listLevels.mockResolvedValue(
        paged([{ ...LEVEL, grades: [GRADE] }])
      );
    });

    test("abre promoción desde la fila vigente y desde el historial", async () => {
      enrolmentsServiceMock.getPromotion.mockReset().mockResolvedValue({
        progression: "promoted",
        eligible_grade_name: "Segundo básico",
        result_source: "live",
        total_subjects: 8,
        failed_subjects: [],
      });
      const user = userEvent.setup();
      renderWithRouter(<EnrolmentsPage />);
      await user.click(
        await screen.findByRole("button", { name: "Consultar promoción" })
      );
      let dialog = await screen.findByRole("dialog", {
        name: "Consultar promoción",
      });
      expect(
        await within(dialog).findByText("Segundo básico")
      ).toBeInTheDocument();
      expect(
        within(dialog).getByText("Luis Perez · EST-1")
      ).toBeInTheDocument();
      expect(enrolmentsServiceMock.getPromotion).toHaveBeenLastCalledWith(
        ENROLMENT.public_id
      );
      await user.click(
        within(dialog).getAllByRole("button", { name: "Cerrar" })[1]
      );
      const studentFilter = screen.getByRole("combobox", {
        name: "Estudiante",
      });
      await user.click(studentFilter);
      // El PR #636 sustituye el selector de catálogo por búsqueda remota.
      if (studentFilter.tagName === "INPUT")
        await user.type(studentFilter, "Luis");
      await user.click(
        await screen.findByRole("option", { name: "Luis Perez · EST-1" })
      );
      await user.click(
        screen.getByRole("tab", { name: "Historial por estudiante" })
      );
      await user.click(
        await screen.findByRole("button", { name: "Consultar promoción" })
      );
      dialog = await screen.findByRole("dialog", {
        name: "Consultar promoción",
      });
      expect(
        await within(dialog).findByText("Segundo básico")
      ).toBeInTheDocument();
      expect(enrolmentsServiceMock.getPromotion).toHaveBeenCalledTimes(2);
    });

    test("muestra nombres en vez de identificadores", async () => {
      renderWithRouter(<EnrolmentsPage />);

      expect(await screen.findByText("Luis Perez · EST-1")).toBeInTheDocument();
      expect(
        screen.getByText("Primero Basico A · Matutina")
      ).toBeInTheDocument();
      expect(screen.getByText("Primero Basico")).toBeInTheDocument();
      expect(screen.queryByText("student-1")).not.toBeInTheDocument();
    });

    test("matricula derivando grado y jornada de la seccion", async () => {
      const user = userEvent.setup();
      renderWithRouter(<EnrolmentsPage />);
      await screen.findByRole("heading", { name: "Matriculas vigentes" });

      await user.click(screen.getByRole("button", { name: "Matricular" }));
      await user.click(screen.getByRole("menuitem", { name: /Un estudiante/ }));
      const form = await screen.findByRole("dialog", {
        name: "Matricular estudiante",
      });
      await user.click(
        within(form).getByRole("combobox", { name: /Estudiante/ })
      );
      await user.click(
        await screen.findByRole("option", { name: "Luis Perez · EST-1" })
      );
      await user.click(screen.getByRole("combobox", { name: /Ciclo escolar/ }));
      await user.click(
        await screen.findByRole("option", { name: "Ciclo 2026 · Activo" })
      );
      await user.click(screen.getByRole("combobox", { name: /Seccion/ }));
      await user.click(
        await screen.findByRole("option", { name: "Primero Basico A" })
      );
      await user.type(screen.getByLabelText(/Vigente desde/), "2026-02-01");
      await user.click(
        screen.getByRole("button", { name: "Confirmar matrícula" })
      );

      // Grado y jornada no se piden: son propiedades de la seccion elegida, y
      // pedirlos aparte solo permitiria contradecirlas.
      expect(enrolmentsServiceMock.register).toHaveBeenCalledWith({
        student_id: "student-1",
        academic_cycle_id: "cycle-2026",
        section_id: "section-a",
        grade_id: "grade-1",
        shift_id: "shift-1",
        effective_on: "2026-02-01",
      });
    });

    test("abre reinscripcion por lotes sin confundirla con altas iniciales", async () => {
      const user = userEvent.setup();
      renderWithRouter(<EnrolmentsPage />);
      await user.click(screen.getByRole("button", { name: "Matricular" }));
      await user.click(
        screen.getByRole("menuitem", { name: /Reinscribir por lotes/ })
      );
      const dialog = await screen.findByRole("dialog", {
        name: "Reinscripción por lotes",
      });
      expect(
        within(dialog).getByText(
          "Elija el ciclo de origen para consultar candidatos."
        )
      ).toBeInTheDocument();
      expect(enrolmentsServiceMock.register).not.toHaveBeenCalled();
      await user.click(within(dialog).getByLabelText("Cerrar"));
      await waitFor(() =>
        expect(
          screen.queryByRole("dialog", { name: "Reinscripción por lotes" })
        ).not.toBeInTheDocument()
      );
    });

    test("matricula a varios estudiantes en una sola pasada", async () => {
      const user = userEvent.setup();
      enrolmentsServiceMock.listSectionOccupancy
        .mockResolvedValueOnce({
          count: 1,
          results: [
            {
              public_id: "section-a",
              academic_cycle_id: "cycle-2026",
              capacity: 30,
              occupied_seats: 12,
              available_seats: 18,
            },
          ],
        })
        .mockResolvedValue({
          count: 1,
          results: [
            {
              public_id: "section-a",
              academic_cycle_id: "cycle-2026",
              capacity: 30,
              occupied_seats: 13,
              available_seats: 17,
            },
          ],
        });
      const OTRO = {
        ...STUDENT,
        public_id: "student-2",
        person: { first_name: "Ines", last_name: "Xoy" },
        student_code: "EST-2",
      };
      studentsServiceMock.listPage.mockResolvedValue(paged([STUDENT, OTRO]));
      enrolmentsServiceMock.listInitialCandidates.mockResolvedValue(
        paged([
          {
            public_id: OTRO.public_id,
            full_name: "Ines Xoy",
            student_code: OTRO.student_code,
          },
        ])
      );
      enrolmentsServiceMock.bulkMatriculate.mockImplementation(
        async (payload) => ({
          preview: payload.preview,
          total: 1,
          succeeded: 1,
          failed: 0,
          results: [
            {
              student_id: "student-2",
              status: payload.preview ? "ready" : "created",
              error: null,
              enrolment_id: payload.preview ? null : "enrolment-2",
            },
          ],
        })
      );
      // ENROLMENT ya cubre a student-1, asi que solo el segundo debe ofrecerse.
      enrolmentsServiceMock.listActive.mockResolvedValue(paged([ENROLMENT]));
      renderWithRouter(<EnrolmentsPage />);
      await screen.findByRole("heading", { name: "Matriculas vigentes" });

      await user.click(screen.getByRole("button", { name: "Matricular" }));
      await user.click(
        screen.getByRole("menuitem", { name: /Altas iniciales por lotes/ })
      );
      const window = await screen.findByRole("dialog", {
        name: "Matriculacion por lotes",
      });

      await user.click(
        within(window).getByRole("combobox", { name: /Ciclo escolar/ })
      );
      await user.click(
        await screen.findByRole("option", { name: "Ciclo 2026 · Activo" })
      );
      await user.click(
        within(window).getByRole("combobox", { name: /Seccion/ })
      );
      await user.click(
        await screen.findByRole("option", { name: "Primero Basico A" })
      );
      await user.type(
        within(window).getByLabelText(/Vigente desde/),
        "2026-03-02"
      );

      // El picker ya no trae el listado completo: hay que escribir para que
      // pida al backend (aqui, el mock) las coincidencias.
      await user.type(
        within(window).getByPlaceholderText(/Buscar por nombre o codigo/),
        "ines"
      );

      expect(
        await within(window).findByLabelText("Ines Xoy · EST-2")
      ).toBeInTheDocument();
      expect(
        within(window).queryByLabelText("Luis Perez · EST-1")
      ).not.toBeInTheDocument();

      await user.click(within(window).getByLabelText("Ines Xoy · EST-2"));
      await user.click(
        within(window).getByRole("button", { name: "Vista previa" })
      );
      await user.click(
        await within(window).findByRole("button", {
          name: "Confirmar matrículas",
        })
      );
      expect(enrolmentsServiceMock.bulkMatriculate).toHaveBeenLastCalledWith({
        section_id: "section-a",
        effective_on: "2026-03-02",
        student_ids: ["student-2"],
        preview: false,
      });
      const occupancy = within(window).getByRole("region", {
        name: "Cupo de la sección",
      });
      expect(await within(occupancy).findByText("17")).toBeInTheDocument();
      expect(
        enrolmentsServiceMock.listSectionOccupancy.mock.calls.length
      ).toBeGreaterThanOrEqual(2);
    });

    test("muestra cupo en el formulario individual unificado", async () => {
      const user = userEvent.setup();
      renderWithRouter(<EnrolmentsPage />);
      await screen.findByText("Luis Perez · EST-1");
      await user.click(screen.getByRole("button", { name: "Matricular" }));
      await user.click(screen.getByRole("menuitem", { name: /Un estudiante/ }));
      const dialog = await screen.findByRole("dialog");
      expect(enrolmentsServiceMock.listSectionOccupancy).not.toHaveBeenCalled();
      await user.click(
        within(dialog).getByRole("combobox", { name: /Ciclo escolar/ })
      );
      await user.click(
        await screen.findByRole("option", { name: "Ciclo 2026 · Activo" })
      );
      await user.click(
        within(dialog).getByRole("combobox", { name: /Seccion/ })
      );
      await user.click(
        await screen.findByRole("option", { name: "Primero Basico A" })
      );
      const occupancy = within(dialog).getByRole("region", {
        name: "Cupo de la sección",
      });
      expect(await within(occupancy).findByText("18")).toBeInTheDocument();
      expect(enrolmentsServiceMock.listSectionOccupancy).toHaveBeenCalledWith({
        academic_cycle_id: "cycle-2026",
        section_id: "section-a",
      });
    });

    test("conserva el formulario y relee cupo después de un rechazo al matricular", async () => {
      enrolmentsServiceMock.register.mockRejectedValueOnce(
        new Error("La sección alcanzó su cupo.")
      );
      const user = userEvent.setup();
      renderWithRouter(<EnrolmentsPage />);
      await screen.findByText("Luis Perez · EST-1");
      await user.click(screen.getByRole("button", { name: "Matricular" }));
      await user.click(screen.getByRole("menuitem", { name: /Un estudiante/ }));
      const dialog = await screen.findByRole("dialog");
      for (const [label, option] of [
        [/Estudiante/, "Luis Perez · EST-1"],
        [/Ciclo escolar/, "Ciclo 2026 · Activo"],
        [/Seccion/, "Primero Basico A"],
      ]) {
        await user.click(within(dialog).getByRole("combobox", { name: label }));
        await user.click(await screen.findByRole("option", { name: option }));
      }
      await within(dialog).findByText("18");
      enrolmentsServiceMock.listSectionOccupancy.mockResolvedValue({
        count: 1,
        results: [
          {
            public_id: "section-a",
            academic_cycle_id: "cycle-2026",
            capacity: 30,
            occupied_seats: 30,
            available_seats: 0,
          },
        ],
      });
      await user.type(
        within(dialog).getByLabelText(/Vigente desde/),
        "2026-02-01"
      );
      await user.click(
        within(dialog).getByRole("button", { name: "Confirmar matrícula" })
      );
      expect(
        await within(dialog).findByText("La sección alcanzó su cupo.")
      ).toBeInTheDocument();
      expect(
        await within(dialog).findByText(/Sección sin vacantes/)
      ).toBeInTheDocument();
      expect(within(dialog).getByLabelText(/Vigente desde/)).toHaveValue(
        "2026-02-01"
      );
    });

    test("muestra las matriculas vigentes", async () => {
      renderWithRouter(<EnrolmentsPage />);

      expect(
        await screen.findByRole("heading", { name: "Matriculas vigentes" })
      ).toBeInTheDocument();
      expect(screen.getByText("Luis Perez · EST-1")).toBeInTheDocument();
      expect(screen.getByText("Activa")).toBeInTheDocument();
    });

    test("filtra en servidor y vuelve a la primera página al cambiar o limpiar filtros", async () => {
      enrolmentsServiceMock.listActive.mockResolvedValue({
        count: 60,
        results: [ENROLMENT],
      });
      const user = userEvent.setup();
      renderWithRouter(<EnrolmentsPage />);
      await screen.findByText("Luis Perez · EST-1");
      await user.click(
        screen.getByRole("button", { name: "Siguiente", exact: true })
      );
      await waitFor(() =>
        expect(enrolmentsServiceMock.listActive).toHaveBeenLastCalledWith(
          expect.objectContaining({ page: 2 })
        )
      );
      await selectOption(user, "Ciclo escolar", "Ciclo 2026 · Activo");
      await waitFor(() =>
        expect(enrolmentsServiceMock.listActive).toHaveBeenLastCalledWith(
          expect.objectContaining({
            page: 1,
            academic_cycle_id: "cycle-2026",
          })
        )
      );
      await selectOption(user, "Grado", "Primero Basico · Basico");
      await screen.findByText(/Página 1 de 1/);
      await selectOption(user, "Sección", "Primero Basico · A · Matutina");
      await waitFor(() =>
        expect(enrolmentsServiceMock.listActive).toHaveBeenLastCalledWith(
          expect.objectContaining({
            page: 1,
            academic_cycle_id: "cycle-2026",
            grade_id: "grade-1",
            section_id: "section-a",
          })
        )
      );
      await selectStudentFilter(user);
      await waitFor(() =>
        expect(enrolmentsServiceMock.listActive).toHaveBeenLastCalledWith(
          expect.objectContaining({
            student_id: "student-1",
            academic_cycle_id: "cycle-2026",
            section_id: "section-a",
          })
        )
      );
      await user.click(
        screen.getByRole("button", { name: "Limpiar", exact: true })
      );
      await waitFor(() =>
        expect(enrolmentsServiceMock.listActive).toHaveBeenLastCalledWith(
          expect.objectContaining({
            page: 1,
            student_id: undefined,
            academic_cycle_id: undefined,
            grade_id: undefined,
            section_id: undefined,
          })
        )
      );
      expect(screen.queryByText(/Página 1 de 1/)).not.toBeInTheDocument();
    }, 15000);

    test("conserva filtros al volver de historial y no filtra el historial por contexto académico", async () => {
      const user = userEvent.setup();
      renderWithRouter(<EnrolmentsPage />);
      await screen.findByText("Luis Perez · EST-1");
      await selectOption(user, "Ciclo escolar", "Ciclo 2026 · Activo");
      await selectStudentFilter(user);
      await user.click(
        screen.getByRole("tab", { name: "Historial por estudiante" })
      );
      await waitFor(() =>
        expect(enrolmentsServiceMock.listHistory).toHaveBeenLastCalledWith(
          expect.objectContaining({ student_id: "student-1" })
        )
      );
      expect(
        enrolmentsServiceMock.listHistory.mock.lastCall[0]
      ).not.toHaveProperty("academic_cycle_id");
      expect(
        screen.queryByRole("group", { name: "Filtros académicos de matrícula" })
      ).not.toBeInTheDocument();
      await user.click(screen.getByRole("tab", { name: "Vigentes" }));
      expect(
        screen.getByRole("combobox", { name: "Ciclo escolar" })
      ).toHaveTextContent("Ciclo 2026");
    });

    test("muestra errores de listado sin descartar el grado seleccionado", async () => {
      enrolmentsServiceMock.listActive.mockImplementation(({ grade_id }) =>
        grade_id
          ? Promise.reject(new Error("No se pudo consultar la matrícula."))
          : Promise.resolve(paged([ENROLMENT]))
      );
      const user = userEvent.setup();
      renderWithRouter(<EnrolmentsPage />);
      await screen.findByText("Luis Perez · EST-1");
      await selectOption(user, "Grado", "Primero Basico · Basico");
      expect(
        await screen.findByText("No se pudo consultar la matrícula.")
      ).toBeInTheDocument();
      expect(screen.getByRole("combobox", { name: "Grado" })).toHaveTextContent(
        "Primero Basico"
      );
    });

    test("el historial pide un estudiante antes de consultar", async () => {
      const user = userEvent.setup();
      renderWithRouter(<EnrolmentsPage />);
      await screen.findByRole("heading", { name: "Matriculas vigentes" });

      await user.click(screen.getByRole("tab", { name: /Historial/ }));

      // El endpoint de historial exige student_id, asi que la pantalla lo pide
      // en vez de disparar una peticion que el backend rechazaria con 400.
      expect(
        screen.getByText(/elija uno en el filtro de arriba/)
      ).toBeInTheDocument();
      expect(enrolmentsServiceMock.listHistory).not.toHaveBeenCalled();
    });

    test("abre movimientos desde la fila con contexto de matricula vigente", async () => {
      const user = userEvent.setup();
      renderWithRouter(<EnrolmentsPage />);
      await screen.findByText("Luis Perez · EST-1");
      await user.click(
        screen.getAllByRole("button", { name: "Movimientos de matrícula" })[0]
      );
      const dialog = await screen.findByRole("dialog", {
        name: "Historial de movimientos",
      });
      expect(
        within(dialog).getByText("Luis Perez · EST-1")
      ).toBeInTheDocument();
      expect(
        within(dialog).getByRole("tab", { name: "Registrar movimiento" })
      ).toBeEnabled();
      expect(enrolmentsServiceMock.listMovements).toHaveBeenCalledWith(
        expect.objectContaining({ student_id: "student-1" })
      );
    });

    test("abre el expediente documental de una matricula", async () => {
      const user = userEvent.setup();
      renderWithRouter(<EnrolmentsPage />);
      await screen.findByText("Luis Perez · EST-1");

      await user.click(
        screen.getAllByRole("button", { name: "Requisitos documentales" })[0]
      );

      expect(
        await screen.findByRole("dialog", { name: "Expediente documental" })
      ).toBeInTheDocument();
      expect(documentsServiceMock.issuanceEligibility).toHaveBeenCalledWith(
        "enr-1"
      );
      expect(
        await screen.findByText(/puede emitir documentos oficiales/)
      ).toBeInTheDocument();
    });

    test("avisa cuando la emision oficial esta bloqueada por requisitos", async () => {
      documentsServiceMock.issuanceEligibility.mockResolvedValue({
        eligible: false,
        blocking_document_codes: ["DPI", "CERT-NAC"],
      });
      const user = userEvent.setup();
      renderWithRouter(<EnrolmentsPage />);
      await screen.findByText("Luis Perez · EST-1");

      await user.click(
        screen.getAllByRole("button", { name: "Requisitos documentales" })[0]
      );

      expect(
        await screen.findByText(/Emision oficial bloqueada/)
      ).toBeInTheDocument();
      expect(screen.getByText("DPI, CERT-NAC")).toBeInTheDocument();
    });
  });

  describe("accesos de traslados", () => {
    test.each(["ingreso", "egreso"])(
      "abre traslado de %s desde Matriculas",
      async (direction) => {
        const user = userEvent.setup();
        studentsServiceMock.listPage.mockResolvedValue(paged([STUDENT]));
        academicsServiceMock.listSections.mockResolvedValue(paged([SECTION]));
        academicsServiceMock.listLevels.mockResolvedValue(
          paged([{ ...LEVEL, grades: [GRADE] }])
        );
        renderWithRouter(<EnrolmentsPage />);
        await screen.findByText("Luis Perez · EST-1");
        await user.click(
          screen.getAllByRole("button", { name: `Traslado de ${direction}` })[0]
        );
        const dialog = await screen.findByRole("dialog", {
          name: `Traslado de ${direction}`,
        });
        if (direction === "ingreso")
          expect(
            within(dialog).getByPlaceholderText(
              "Buscar estudiante por nombre o código"
            )
          ).toBeInTheDocument();
        else
          expect(
            within(dialog).getByText("Luis Perez · EST-1")
          ).toBeInTheDocument();
        expect(screen.getAllByRole("dialog")).toHaveLength(1);
      }
    );
  });

  describe("DocumentTypesPage", () => {
    test("lista el catalogo institucional de tipos", async () => {
      renderWithRouter(<DocumentTypesPage />);

      expect(await screen.findByText("Constancia")).toBeInTheDocument();
      expect(screen.getByText("Reporte")).toBeInTheDocument();
      expect(screen.getByText("certificate")).toBeInTheDocument();
    });

    test("da de alta un tipo nuevo sin tocar el sistema", async () => {
      const user = userEvent.setup();
      renderWithRouter(<DocumentTypesPage />);
      await screen.findByText("Constancia");

      await user.click(screen.getByRole("button", { name: /Nuevo tipo/ }));
      const window = await screen.findByRole("dialog", {
        name: "Nuevo tipo de documento",
      });

      await user.type(
        within(window).getByLabelText(/^Nombre visible/),
        "Finiquito"
      );
      await user.type(within(window).getByLabelText(/^Codigo/), "finiquito");
      await user.click(
        within(window).getByRole("button", { name: "Crear tipo" })
      );

      expect(documentsServiceMock.createType).toHaveBeenCalledWith(
        expect.objectContaining({ code: "finiquito", label: "Finiquito" })
      );
    });

    test("editar no ofrece el codigo, que es inmutable", async () => {
      const user = userEvent.setup();
      renderWithRouter(<DocumentTypesPage />);
      await screen.findByText("Constancia");

      await user.click(screen.getAllByRole("button", { name: "Editar" })[0]);

      const window = await screen.findByRole("dialog", {
        name: "Editar Constancia",
      });
      expect(
        within(window).queryByLabelText(/^Codigo/)
      ).not.toBeInTheDocument();
    });
  });

  describe("TemplatesPage", () => {
    beforeEach(() => {
      documentsServiceMock.listTemplateIssuanceUses.mockResolvedValue([
        {
          code: "enrolment_certificate",
          label: "Constancia de inscripcion",
          active_template: null,
          uses_fallback: true,
        },
        {
          code: "study_certificate",
          label: "Certificado de estudios",
          active_template: null,
          uses_fallback: true,
        },
      ]);
    });

    test("el selector de tipo se llena con el catalogo del backend", async () => {
      const user = userEvent.setup();
      renderWithRouter(<TemplatesPage />);
      await screen.findByText("Constancia de inscripcion");

      await user.click(screen.getByRole("button", { name: /Nueva plantilla/ }));
      const window = await screen.findByRole("dialog", {
        name: "Nueva plantilla documental",
      });

      await user.click(within(window).getByLabelText(/^Tipo/));

      expect(
        await screen.findByRole("option", { name: "Constancia" })
      ).toBeInTheDocument();
      expect(
        screen.getByRole("option", { name: "Reporte" })
      ).toBeInTheDocument();
    });

    test("lista las plantillas con su tipo y encabezado", async () => {
      renderWithRouter(<TemplatesPage />);

      expect(
        await screen.findByText("Constancia de inscripcion")
      ).toBeInTheDocument();
      expect(screen.getByText("Constancia")).toBeInTheDocument();
      expect(screen.getByText("Institucional")).toBeInTheDocument();
    });

    test("editar no ofrece el codigo, que es inmutable", async () => {
      const user = userEvent.setup();
      renderWithRouter(<TemplatesPage />);
      await screen.findByText("Constancia de inscripcion");

      await user.click(screen.getByRole("button", { name: "Editar" }));

      const window = await screen.findByRole("dialog", {
        name: "Editar Constancia de inscripcion",
      });
      expect(
        within(window).queryByLabelText(/^Codigo/)
      ).not.toBeInTheDocument();
      expect(
        within(window).getByText(/genera una version nueva/)
      ).toBeInTheDocument();
    });

    test("las etiquetas sensibles quedan detras de un interruptor explicito", async () => {
      const user = userEvent.setup();
      renderWithRouter(<TemplatesPage />);
      await screen.findByText("Constancia de inscripcion");

      await user.click(
        screen.getByRole("button", { name: /Etiquetas disponibles/ })
      );
      const tagsWindow = await screen.findByRole("dialog", {
        name: "Etiquetas dinamicas disponibles",
      });

      expect(documentsServiceMock.listFieldTags).toHaveBeenCalledWith(
        expect.objectContaining({ include_sensitive: false })
      );

      await user.click(within(tagsWindow).getByLabelText(/datos sensibles/));

      expect(documentsServiceMock.listFieldTags).toHaveBeenCalledWith(
        expect.objectContaining({ include_sensitive: true })
      );
    });

    test("la vista previa usa datos de muestra sin guardar ni emitir", async () => {
      documentsServiceMock.previewTemplate.mockResolvedValue({
        content: "Constancia para Estudiante de ejemplo",
        markers: ["student.full_name"],
        marker_count: 1,
        content_type: "application/pdf",
        pdf_base64: "JVBERi0xLjQK",
      });
      const user = userEvent.setup();
      renderWithRouter(<TemplatesPage />);
      await screen.findByText("Constancia de inscripcion");

      await user.click(screen.getByRole("button", { name: "Vista previa" }));

      expect(
        await screen.findByRole("dialog", {
          name: "Vista previa: Constancia de inscripcion",
        })
      ).toBeInTheDocument();
      expect(documentsServiceMock.previewTemplate).toHaveBeenCalledWith(
        "tpl-1",
        expect.objectContaining({
          "student.full_name": "Estudiante de ejemplo",
        })
      );
      expect(documentsServiceMock.createTemplate).not.toHaveBeenCalled();
      expect(documentsServiceMock.updateTemplate).not.toHaveBeenCalled();
      expect(
        screen.getByLabelText("Documento PDF de vista previa")
      ).toHaveAttribute("src", "data:application/pdf;base64,JVBERi0xLjQK");
    });
  });

  describe("AlertsPage", () => {
    test("arranca filtrando las alertas sin atender", async () => {
      renderWithRouter(<AlertsPage />);

      await screen.findByRole("heading", { name: "Alertas registradas" });
      // El tablero es para atender: el filtro por defecto es lo pendiente.
      expect(reportingServiceMock.listAlerts).toHaveBeenCalledWith(
        expect.objectContaining({ acknowledged: false })
      );

      // "Frecuencia de ausencias" aparece tambien como etiqueta del indicador,
      // asi que la busqueda se acota a la tabla.
      const table = await screen.findByRole("table");
      expect(
        within(table).getByText("Frecuencia de ausencias")
      ).toBeInTheDocument();
      expect(within(table).getByText("Sin atender")).toBeInTheDocument();
      expect(
        within(table).getByRole("link", { name: /Luis Perez/ })
      ).toHaveAttribute("href", "/app/alumnos/student-1");
      expect(screen.getByRole("alert")).toHaveTextContent(
        "alertas operativas del día"
      );
    });

    test("los indicadores piden una sola fila y muestran el count del backend", async () => {
      reportingServiceMock.listAlerts.mockImplementation(async (params) => {
        if (params.page_size !== 1) return paged([ALERT]);
        const count =
          params.acknowledged === false
            ? 37
            : params.alert_type === "frecuencia_ausencias"
              ? 41
              : 58;
        return { count, results: [ALERT] };
      });
      renderWithRouter(<AlertsPage />);

      expect(await screen.findByText("37")).toBeInTheDocument();
      expect(screen.getByText("58")).toBeInTheDocument();
      expect(screen.getByText("41")).toBeInTheDocument();
      expect(reportingServiceMock.listAlerts).toHaveBeenCalledWith({
        acknowledged: false,
        page_size: 1,
      });
      expect(reportingServiceMock.listAlerts).toHaveBeenCalledWith({
        page_size: 1,
      });
      expect(reportingServiceMock.listAlerts).toHaveBeenCalledWith({
        alert_type: "frecuencia_ausencias",
        page_size: 1,
      });
    });

    test("atender pide confirmacion y luego llama al backend", async () => {
      const user = userEvent.setup();
      renderWithRouter(<AlertsPage />);
      await screen.findByText("Frecuencia de ausencias");

      await user.click(screen.getByRole("button", { name: "Atender" }));
      expect(reportingServiceMock.acknowledge).not.toHaveBeenCalled();

      await user.click(
        screen.getByRole("button", { name: "Si, marcar atendida" })
      );
      expect(reportingServiceMock.acknowledge).toHaveBeenCalledWith("alert-1");
    });
  });
});
