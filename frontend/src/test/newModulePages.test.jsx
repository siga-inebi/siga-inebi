import { screen, within } from "@testing-library/react";
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
  listActive: vi.fn(),
  listHistory: vi.fn(),
  create: vi.fn(),
  matriculate: vi.fn(),
  reenrol: vi.fn(),
  listDocuments: vi.fn(),
  addDocument: vi.fn(),
}));

const documentsServiceMock = vi.hoisted(() => ({
  listTemplates: vi.fn(),
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

const attendanceServiceMock = vi.hoisted(() => ({
  listJornadaParameters: vi.fn(),
  createJornadaParameters: vi.fn(),
  listEvents: vi.fn(),
  createEvent: vi.fn(),
  eventResolution: vi.fn(),
  dayStatus: vi.fn(),
  closeJornada: vi.fn(),
  listAlerts: vi.fn(),
  listControlPoints: vi.fn(),
  recordScan: vi.fn(),
  listPresence: vi.fn(),
  attendancePercentage: vi.fn(),
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

vi.mock("@attendance/attendanceService.js", async () => {
  const actual = await vi.importActual("@attendance/attendanceService.js");
  return { ...actual, attendanceService: attendanceServiceMock };
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
import { CyclesPage } from "@cycles/CyclesPage.jsx";
import { EnrolmentsPage } from "@enrolments/EnrolmentsPage.jsx";
import { TeachingAssignmentsPage } from "@academics/TeachingAssignmentsPage.jsx";
import { TemplatesPage } from "@documents/TemplatesPage.jsx";
import { todayInputValue } from "@shared/utils/format.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
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

/** La misma seccion, tal como queda tras clonar la estructura al ciclo nuevo. */
const NEXT_CYCLE_SECTION = {
  ...SECTION,
  public_id: "section-a-2027",
  academic_cycle_id: "cycle-2027",
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
    enrolmentsServiceMock.listDocuments
      .mockReset()
      .mockResolvedValue(paged([]));
    documentsServiceMock.issuanceEligibility
      .mockReset()
      .mockResolvedValue({ eligible: true, blocking_document_codes: [] });

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

    attendanceServiceMock.listEvents.mockReset().mockResolvedValue(paged([]));
    attendanceServiceMock.listAlerts.mockReset().mockResolvedValue(paged([]));
    attendanceServiceMock.listJornadaParameters
      .mockReset()
      .mockResolvedValue(paged([]));
    attendanceServiceMock.dayStatus
      .mockReset()
      .mockResolvedValue({ status: "presente", entry_event: null });
    attendanceServiceMock.listControlPoints
      .mockReset()
      .mockResolvedValue(paged([]));
    attendanceServiceMock.listPresence.mockReset().mockResolvedValue(paged([]));
    attendanceServiceMock.attendancePercentage.mockReset();
    attendanceServiceMock.recordScan.mockReset();

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

  describe("CyclesPage", () => {
    test("lista los ciclos y marca el vigente", async () => {
      renderWithRouter(<CyclesPage />);

      expect(await screen.findByText("Ciclo 2026")).toBeInTheDocument();
      expect(screen.getByText("Vigente")).toBeInTheDocument();
      // El estado del ciclo se muestra siempre: es la raiz temporal del sistema.
      expect(screen.getByText("Borrador")).toBeInTheDocument();
    });

    test("solo ofrece activar los ciclos en borrador", async () => {
      renderWithRouter(<CyclesPage />);
      await screen.findByText("Ciclo 2026");

      // Un ciclo ya activo o cerrado no se activa: hay un solo boton, el del borrador.
      expect(screen.getAllByRole("button", { name: "Activar" })).toHaveLength(
        1
      );
    });

    test("activar pide confirmacion antes de llamar al backend", async () => {
      const user = userEvent.setup();
      renderWithRouter(<CyclesPage />);
      await screen.findByText("Ciclo 2026");

      await user.click(screen.getByRole("button", { name: "Activar" }));
      expect(cyclesServiceMock.activate).not.toHaveBeenCalled();
      expect(
        screen.getByText(/El ciclo activo anterior queda cerrado/)
      ).toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: "Si, activar" }));
      expect(cyclesServiceMock.activate).toHaveBeenCalledWith("cycle-2027");
    });

    test("el ciclo se define por su ano: nombre y vigencia se derivan", async () => {
      const user = userEvent.setup();
      renderWithRouter(<CyclesPage />);
      await screen.findByText("Ciclo 2026");

      await user.click(screen.getByRole("button", { name: "Nuevo ciclo" }));

      // Un solo dato a elegir; los otros tres llegan calculados.
      expect(await screen.findByDisplayValue("Ciclo 2027")).toBeInTheDocument();
      expect(screen.getByDisplayValue("2027-01-15")).toBeInTheDocument();
      expect(screen.getByDisplayValue("2027-10-29")).toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: "Crear ciclo" }));

      expect(cyclesServiceMock.create).toHaveBeenCalledWith({
        year: 2027,
        name: "Ciclo 2027",
        starts_on: "2027-01-15",
        ends_on: "2027-10-29",
        description: "",
      });
    });

    test("cambiar el ano recalcula nombre y vigencia", async () => {
      const user = userEvent.setup();
      renderWithRouter(<CyclesPage />);
      await screen.findByText("Ciclo 2026");

      await user.click(screen.getByRole("button", { name: "Nuevo ciclo" }));
      await screen.findByDisplayValue("Ciclo 2027");

      await user.click(screen.getByLabelText(/^Ano del ciclo/));
      await user.click(await screen.findByRole("option", { name: "2029" }));

      // El ano es lo que determina las fechas: dejar una de 2027 debajo de un
      // ciclo 2029 seria peor que perder una edicion manual.
      expect(await screen.findByDisplayValue("Ciclo 2029")).toBeInTheDocument();
      expect(screen.getByDisplayValue("2029-01-15")).toBeInTheDocument();
    });

    test("el ano se elige de una lista, no se teclea", async () => {
      const user = userEvent.setup();
      renderWithRouter(<CyclesPage />);
      await screen.findByText("Ciclo 2026");

      await user.click(screen.getByRole("button", { name: "Nuevo ciclo" }));

      // Un rango chico y conocido: "2072" no se distingue de "2027" al leerlo
      // de reojo, y un ano equivocado corre en silencio todo lo que cuelga del
      // ciclo.
      expect(
        await screen.findByRole("combobox", { name: /Ano del ciclo/ })
      ).toBeInTheDocument();
    });

    test("clonar ofrece copiar las asignaciones docentes", async () => {
      const user = userEvent.setup();
      cyclesServiceMock.clone.mockResolvedValue(DRAFT_CYCLE);
      renderWithRouter(<CyclesPage />);
      await screen.findByText("Ciclo 2026");

      await user.click(
        screen.getAllByRole("button", {
          name: "Clonar estructura a un ciclo nuevo",
        })[0]
      );
      await screen.findByDisplayValue("Ciclo 2027");
      await user.click(
        screen.getByLabelText(/Copiar tambien las asignaciones docentes/)
      );
      await user.click(
        screen.getByRole("button", { name: "Clonar estructura" })
      );

      expect(cyclesServiceMock.clone).toHaveBeenCalledWith(
        "cycle-2026",
        expect.objectContaining({ include_teaching_assignments: true })
      );
    });

    test("el detalle historico es de solo lectura", async () => {
      const user = userEvent.setup();
      renderWithRouter(<CyclesPage />);
      await screen.findByText("Ciclo 2026");

      await user.click(
        screen.getAllByRole("button", { name: "Ver detalle historico" })[0]
      );

      const window = await screen.findByRole("dialog", { name: "Ciclo 2026" });
      expect(cyclesServiceMock.get).toHaveBeenCalledWith("cycle-2026");
      expect(
        within(window).getByText(
          "Estructura registrada para este ciclo. Solo consulta."
        )
      ).toBeInTheDocument();
      expect(
        within(window).queryByRole("button", { name: /Guardar/ })
      ).not.toBeInTheDocument();
    });
  });

  describe("EnrolmentsPage", () => {
    beforeEach(() => {
      studentsServiceMock.listPage.mockResolvedValue(paged([STUDENT]));
      academicsServiceMock.listSections.mockResolvedValue(paged([SECTION]));
      // El catalogo de grados pide niveles con ?expand=grades, no un
      // /levels/{id}/grades/ por nivel: el mock ya trae el grado anidado.
      academicsServiceMock.listLevels.mockResolvedValue(
        paged([{ ...LEVEL, grades: [GRADE] }])
      );
    });

    test("muestra nombres en vez de identificadores", async () => {
      renderWithRouter(<EnrolmentsPage />);

      expect(await screen.findByText("Luis Perez · EST-1")).toBeInTheDocument();
      expect(screen.getByText("Primero Basico A")).toBeInTheDocument();
      expect(screen.getByText("Primero Basico · Basico")).toBeInTheDocument();
      expect(screen.queryByText("student-1")).not.toBeInTheDocument();
    });

    test("matricula derivando grado y jornada de la seccion", async () => {
      const user = userEvent.setup();
      renderWithRouter(<EnrolmentsPage />);
      await screen.findByRole("heading", { name: "Matriculas vigentes" });

      await user.click(screen.getByRole("button", { name: "Nueva matricula" }));
      await user.click(screen.getByRole("combobox", { name: /Estudiante/ }));
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
      await user.click(screen.getByRole("button", { name: "Matricular" }));

      // Grado y jornada no se piden: son propiedades de la seccion elegida, y
      // pedirlos aparte solo permitiria contradecirlas.
      expect(enrolmentsServiceMock.matriculate).toHaveBeenCalledWith({
        student_id: "student-1",
        academic_cycle_id: "cycle-2026",
        section_id: "section-a",
        grade_id: "grade-1",
        shift_id: "shift-1",
        effective_on: "2026-02-01",
      });
    });

    test("matricula a varios estudiantes en una sola pasada", async () => {
      const user = userEvent.setup();
      const OTRO = {
        ...STUDENT,
        public_id: "student-2",
        person: { first_name: "Ines", last_name: "Xoy" },
        student_code: "EST-2",
      };
      studentsServiceMock.listPage.mockResolvedValue(paged([STUDENT, OTRO]));
      // ENROLMENT ya cubre a student-1, asi que solo el segundo debe ofrecerse.
      enrolmentsServiceMock.listActive.mockResolvedValue(paged([ENROLMENT]));
      renderWithRouter(<EnrolmentsPage />);
      await screen.findByRole("heading", { name: "Matriculas vigentes" });

      await user.click(
        screen.getByRole("button", { name: "Matricular por lotes" })
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
        within(window).getByRole("button", { name: /Matricular 1 estudiante/ })
      );

      expect(enrolmentsServiceMock.matriculate).toHaveBeenCalledWith({
        student_id: "student-2",
        academic_cycle_id: "cycle-2026",
        grade_id: "grade-1",
        shift_id: "shift-1",
        section_id: "section-a",
        effective_on: "2026-03-02",
      });
    });

    test("muestra las matriculas vigentes", async () => {
      renderWithRouter(<EnrolmentsPage />);

      expect(
        await screen.findByRole("heading", { name: "Matriculas vigentes" })
      ).toBeInTheDocument();
      expect(screen.getByText("Luis Perez · EST-1")).toBeInTheDocument();
      expect(screen.getByText("Activa")).toBeInTheDocument();
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

  describe("TemplatesPage", () => {
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
    });
  });

  describe("AttendancePage", () => {
    test("abre la vista previa de camara sin registrar movimientos", async () => {
      const user = userEvent.setup();
      renderWithRouter(<AttendancePage />);

      await user.click(screen.getByRole("button", { name: "Abrir camara" }));

      expect(
        await screen.findByRole("dialog", { name: "Vista previa de camara" })
      ).toBeInTheDocument();
      expect(attendanceServiceMock.createEvent).not.toHaveBeenCalled();
    });

    test("el estado del dia arranca en hoy y solo pide estudiante y jornada", async () => {
      const user = userEvent.setup();
      studentsServiceMock.listPage.mockResolvedValue(paged([STUDENT]));
      academicsServiceMock.listCampuses.mockResolvedValue(paged([CAMPUS]));
      academicsServiceMock.listCampusShifts.mockResolvedValue(paged([SHIFT]));
      renderWithRouter(<AttendancePage />);

      // Escopado a la tarjeta: "Porcentaje de asistencia" repite los mismos
      // campos y boton ("Estudiante", "Jornada", "Consultar").
      const card = (
        await screen.findByRole("heading", { name: "Estado del dia" })
      ).closest("section");
      const scoped = within(card);

      // La fecha ya viene puesta en hoy, que es lo que se consulta casi siempre.
      expect(scoped.getByLabelText(/^Fecha/)).toHaveValue(todayInputValue());
      expect(scoped.getByRole("button", { name: /Consultar/ })).toBeDisabled();

      await user.click(scoped.getByRole("combobox", { name: /Estudiante/ }));
      await user.click(
        await screen.findByRole("option", { name: "Luis Perez · EST-1" })
      );
      await user.click(scoped.getByRole("combobox", { name: /Jornada/ }));
      await user.click(
        await screen.findByRole("option", { name: "Matutina · Sede Central" })
      );

      expect(scoped.getByRole("button", { name: /Consultar/ })).toBeEnabled();
      expect(attendanceServiceMock.dayStatus).not.toHaveBeenCalled();
    });

    test("el estado del dia no consulta sin fecha", async () => {
      const user = userEvent.setup();
      studentsServiceMock.listPage.mockResolvedValue(paged([STUDENT]));
      academicsServiceMock.listCampuses.mockResolvedValue(paged([CAMPUS]));
      academicsServiceMock.listCampusShifts.mockResolvedValue(paged([SHIFT]));
      renderWithRouter(<AttendancePage />);

      const card = (
        await screen.findByRole("heading", { name: "Estado del dia" })
      ).closest("section");
      const scoped = within(card);

      await user.click(scoped.getByRole("combobox", { name: /Estudiante/ }));
      await user.click(
        await screen.findByRole("option", { name: "Luis Perez · EST-1" })
      );
      await user.click(scoped.getByRole("combobox", { name: /Jornada/ }));
      await user.click(
        await screen.findByRole("option", { name: "Matutina · Sede Central" })
      );
      await user.clear(scoped.getByLabelText(/^Fecha/));

      // El endpoint exige los tres: consultar con dos devolveria un 400 en vez
      // de un resultado.
      expect(scoped.getByRole("button", { name: /Consultar/ })).toBeDisabled();
      expect(attendanceServiceMock.dayStatus).not.toHaveBeenCalled();
    });

    test('el boton "Hoy" repone la fecha del dia', async () => {
      const user = userEvent.setup();
      renderWithRouter(<AttendancePage />);

      const card = (
        await screen.findByRole("heading", { name: "Estado del dia" })
      ).closest("section");
      const scoped = within(card);
      const dateInput = scoped.getByLabelText(/^Fecha/);

      await user.clear(dateInput);
      expect(dateInput).toHaveValue("");

      await user.click(
        scoped.getByRole("button", { name: "Usar la fecha de hoy" })
      );

      expect(dateInput).toHaveValue(todayInputValue());
    });

    test("el movimiento se registra eligiendo estudiante y jornada", async () => {
      const user = userEvent.setup();
      studentsServiceMock.listPage.mockResolvedValue(paged([STUDENT]));
      academicsServiceMock.listCampuses.mockResolvedValue(paged([CAMPUS]));
      academicsServiceMock.listCampusShifts.mockResolvedValue(paged([SHIFT]));
      renderWithRouter(<AttendancePage />);
      await screen.findByRole("heading", { name: "Movimientos" });

      await user.click(
        screen.getByRole("button", { name: "Registrar movimiento" })
      );
      const form = await screen.findByRole("dialog", {
        name: "Nuevo movimiento de asistencia",
      });

      await user.click(
        within(form).getByRole("combobox", { name: /Estudiante/ })
      );
      await user.click(
        await screen.findByRole("option", { name: "Luis Perez · EST-1" })
      );
      await user.click(within(form).getByRole("combobox", { name: /Jornada/ }));
      await user.click(
        await screen.findByRole("option", { name: "Matutina · Sede Central" })
      );
      // Las dos fechas llegan en hoy: un movimiento se registra el dia que
      // ocurre, y tipearlas dos veces era el paso mas repetido del formulario.
      await user.click(
        within(form).getByRole("button", { name: "Registrar movimiento" })
      );

      expect(attendanceServiceMock.createEvent).toHaveBeenCalledWith(
        expect.objectContaining({
          student_id: "student-1",
          shift_id: "shift-1",
          event_date: todayInputValue(),
          captured_at: todayInputValue(),
        })
      );
    });

    test("muestra el registro de movimientos y sus alertas", async () => {
      renderWithRouter(<AttendancePage />);

      expect(
        await screen.findByRole("heading", { name: "Movimientos" })
      ).toBeInTheDocument();
      expect(
        screen.getByText("Todavia no hay movimientos registrados.")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Sin alertas de asistencia registradas.")
      ).toBeInTheDocument();
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

  describe("TeachingAssignmentsPage", () => {
    beforeEach(() => {
      academicsServiceMock.listSections.mockResolvedValue(paged([SECTION]));
      academicsServiceMock.listSubjects.mockResolvedValue(paged([SUBJECT]));
    });

    test("lista el historial y distingue la vigencia", async () => {
      renderWithRouter(<TeachingAssignmentsPage />);

      expect(await screen.findByText("Ana Lopez · EMP-1")).toBeInTheDocument();
      expect(screen.getByText("Vigente")).toBeInTheDocument();
    });

    test("muestra nombres en vez de identificadores en el historial", async () => {
      renderWithRouter(<TeachingAssignmentsPage />);

      expect(await screen.findByText("Primero Basico A")).toBeInTheDocument();
      expect(screen.getByText("Matematica (MAT)")).toBeInTheDocument();
      expect(screen.getByText("Ciclo 2026 · Activo")).toBeInTheDocument();
      expect(screen.queryByText("section-a")).not.toBeInTheDocument();
      expect(screen.queryByText("subject-mat")).not.toBeInTheDocument();
    });

    test("la seccion solo se puede elegir despues del ciclo", async () => {
      const user = userEvent.setup();
      renderWithRouter(<TeachingAssignmentsPage />);
      await screen.findByText("Vigente");

      await user.click(
        screen.getByRole("button", { name: "Nueva asignacion" })
      );

      // Sin ciclo elegido el catalogo de secciones no aplica: ofrecer las de
      // otro ciclo terminaria en un rechazo del backend al guardar.
      expect(screen.getByRole("combobox", { name: /Seccion/ })).toHaveAttribute(
        "aria-disabled",
        "true"
      );

      await user.click(screen.getByRole("combobox", { name: /Ciclo escolar/ }));
      await user.click(
        await screen.findByRole("option", { name: "Ciclo 2026 · Activo" })
      );

      await user.click(screen.getByRole("combobox", { name: /Seccion/ }));
      expect(
        await screen.findByRole("option", { name: "Primero Basico A" })
      ).toBeInTheDocument();
    });

    test("asigna varios cursos de una seccion en un solo paso", async () => {
      const user = userEvent.setup();
      academicsServiceMock.listSubjects.mockResolvedValue(
        paged([
          SUBJECT,
          {
            ...SUBJECT,
            public_id: "subject-com",
            name: "Comunicacion",
            code: "COM",
          },
        ])
      );
      // El historial ya cubre Matematica en esa seccion, asi que el lote solo
      // debe ofrecer (y crear) el curso que sigue sin docente.
      academicsServiceMock.listTeachingAssignmentHistory.mockResolvedValue(
        paged([ASSIGNMENT])
      );
      renderWithRouter(<TeachingAssignmentsPage />);
      await screen.findByText("Vigente");

      await user.click(
        screen.getByRole("button", { name: "Asignar por lotes" })
      );
      const window = await screen.findByRole("dialog", {
        name: "Asignacion docente por lotes",
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

      expect(
        await within(window).findByText("Matematica (MAT)")
      ).toBeInTheDocument();
      expect(within(window).getByText("Ana Lopez · EMP-1")).toBeInTheDocument();

      // Solo Comunicacion queda pendiente, asi que hay un unico selector de
      // docente en la tabla: el atajo "aplicar a todos" no aparece con uno solo.
      await user.click(
        within(window).getByRole("combobox", { name: "Docente" })
      );
      await user.click(
        await screen.findByRole("option", { name: "Ana Lopez · EMP-1" })
      );

      await user.click(
        within(window).getByRole("button", { name: /Asignar 1 curso/ })
      );

      expect(
        academicsServiceMock.createTeachingAssignment
      ).toHaveBeenCalledTimes(1);
      expect(
        academicsServiceMock.createTeachingAssignment
      ).toHaveBeenCalledWith({
        academic_cycle_id: "cycle-2026",
        section_id: "section-a",
        subject_id: "subject-com",
        teacher_id: "teacher-1",
        starts_on: "2026-03-02",
      });
    });

    test("abrir Asignar por lotes no vuelve a pedir los catalogos que la pagina ya cargo", async () => {
      // Antes de la cache compartida, este modal llamaba a sus propios
      // useCycleCatalog/useSectionCatalog/useSubjectCatalog/useTeacherCatalog
      // y volvia a pedir los 4 catalogos desde cero al abrirse, aunque la
      // pagina ya los tuviera. Con useCatalogOptions respaldado por
      // react-query, ambos consumidores resuelven contra la misma query.
      const user = userEvent.setup();
      renderWithRouter(<TeachingAssignmentsPage />);
      await screen.findByText("Vigente");

      expect(cyclesServiceMock.list).toHaveBeenCalledTimes(1);
      expect(academicsServiceMock.listSections).toHaveBeenCalledTimes(1);
      expect(academicsServiceMock.listSubjects).toHaveBeenCalledTimes(1);
      expect(teachersServiceMock.listPage).toHaveBeenCalledTimes(1);

      await user.click(
        screen.getByRole("button", { name: "Asignar por lotes" })
      );
      await screen.findByRole("dialog", {
        name: "Asignacion docente por lotes",
      });

      expect(cyclesServiceMock.list).toHaveBeenCalledTimes(1);
      expect(academicsServiceMock.listSections).toHaveBeenCalledTimes(1);
      expect(academicsServiceMock.listSubjects).toHaveBeenCalledTimes(1);
      expect(teachersServiceMock.listPage).toHaveBeenCalledTimes(1);
    });

    test("clonar trae el ciclo anterior resuelto y espera confirmacion", async () => {
      const user = userEvent.setup();
      // Misma seccion en los dos ciclos: identificador distinto, pero el mismo
      // grado, jornada y nombre, que es como se reconoce entre ciclos.
      academicsServiceMock.listSections.mockResolvedValue(
        paged([SECTION, NEXT_CYCLE_SECTION])
      );
      // El ciclo nuevo no tiene nada asignado; el listado sin filtro y el ciclo
      // origen si.
      academicsServiceMock.listTeachingAssignmentHistory.mockImplementation(
        ({ academic_cycle_id: cycleId }) =>
          Promise.resolve(
            cycleId === "cycle-2027" ? paged([]) : paged([ASSIGNMENT])
          )
      );
      renderWithRouter(<TeachingAssignmentsPage />);
      await screen.findByText("Vigente");

      await user.click(
        screen.getByRole("button", { name: "Clonar en ciclo nuevo" })
      );
      const window = await screen.findByRole("dialog", {
        name: "Clonar asignaciones en un ciclo nuevo",
      });

      await user.click(
        within(window).getByRole("combobox", { name: /Copiar desde/ })
      );
      await user.click(
        await screen.findByRole("option", { name: "Ciclo 2026 · Activo" })
      );
      await user.click(
        within(window).getByRole("combobox", { name: /Copiar hacia/ })
      );
      await user.click(
        await screen.findByRole("option", { name: "Ciclo 2027 · Borrador" })
      );

      // La asignacion del ano pasado llega resuelta: seccion, curso y docente.
      expect(
        await within(window).findByText("Primero Basico A")
      ).toBeInTheDocument();
      expect(within(window).getByText("Matematica (MAT)")).toBeInTheDocument();
      // Dos veces: la columna del ciclo anterior y el selector ya prellenado con
      // ese mismo docente, que es lo que se va a crear si nadie lo cambia.
      expect(within(window).getAllByText("Ana Lopez · EMP-1")).toHaveLength(2);

      // Nada se guardo hasta aca: clonar propone, la persona confirma.
      expect(
        academicsServiceMock.createTeachingAssignment
      ).not.toHaveBeenCalled();

      await user.click(
        within(window).getByRole("button", { name: /Clonar 1 asignacion/ })
      );

      expect(
        academicsServiceMock.createTeachingAssignment
      ).toHaveBeenCalledWith({
        academic_cycle_id: "cycle-2027",
        // La seccion del ciclo NUEVO, no la del origen.
        section_id: "section-a-2027",
        subject_id: "subject-mat",
        teacher_id: "teacher-1",
        // Propuesta: el inicio del ciclo destino.
        starts_on: "2026-01-15",
      });
    });

    test("clonar avisa cuando el ciclo nuevo no tiene la seccion", async () => {
      const user = userEvent.setup();
      // Solo existe la seccion del ciclo origen: la estructura del ciclo nuevo
      // todavia no se clono.
      academicsServiceMock.listSections.mockResolvedValue(paged([SECTION]));
      // El ciclo nuevo no tiene nada asignado; el listado sin filtro y el ciclo
      // origen si.
      academicsServiceMock.listTeachingAssignmentHistory.mockImplementation(
        ({ academic_cycle_id: cycleId }) =>
          Promise.resolve(
            cycleId === "cycle-2027" ? paged([]) : paged([ASSIGNMENT])
          )
      );
      renderWithRouter(<TeachingAssignmentsPage />);
      await screen.findByText("Vigente");

      await user.click(
        screen.getByRole("button", { name: "Clonar en ciclo nuevo" })
      );
      const window = await screen.findByRole("dialog", {
        name: "Clonar asignaciones en un ciclo nuevo",
      });
      await user.click(
        within(window).getByRole("combobox", { name: /Copiar desde/ })
      );
      await user.click(
        await screen.findByRole("option", { name: "Ciclo 2026 · Activo" })
      );
      await user.click(
        within(window).getByRole("combobox", { name: /Copiar hacia/ })
      );
      await user.click(
        await screen.findByRole("option", { name: "Ciclo 2027 · Borrador" })
      );

      // Decirlo aca evita que alguien busque el problema en el docente o en el
      // curso, cuando lo que falta es la estructura del ciclo.
      // El aviso arriba y la celda de la fila dicen lo mismo.
      expect(
        await within(window).findAllByText(/sin seccion equivalente/i)
      ).not.toHaveLength(0);
      expect(
        within(window).getByRole("button", { name: /Clonar 0 asignaciones/ })
      ).toBeDisabled();
    });

    test("crea la asignacion enviando los identificadores del catalogo", async () => {
      const user = userEvent.setup();
      renderWithRouter(<TeachingAssignmentsPage />);
      await screen.findByText("Vigente");

      await user.click(
        screen.getByRole("button", { name: "Nueva asignacion" })
      );
      await user.click(screen.getByRole("combobox", { name: /Ciclo escolar/ }));
      await user.click(
        await screen.findByRole("option", { name: "Ciclo 2026 · Activo" })
      );
      await user.click(screen.getByRole("combobox", { name: /Seccion/ }));
      await user.click(
        await screen.findByRole("option", { name: "Primero Basico A" })
      );
      await user.click(screen.getByRole("combobox", { name: /Curso/ }));
      await user.click(
        await screen.findByRole("option", { name: "Matematica (MAT)" })
      );
      await user.click(screen.getByRole("combobox", { name: /Docente/ }));
      await user.click(
        await screen.findByRole("option", { name: "Ana Lopez · EMP-1" })
      );
      await user.type(screen.getByLabelText(/Vigente desde/), "2026-03-02");
      await user.click(
        screen.getByRole("button", { name: "Crear asignacion" })
      );

      expect(
        academicsServiceMock.createTeachingAssignment
      ).toHaveBeenCalledWith({
        academic_cycle_id: "cycle-2026",
        section_id: "section-a",
        subject_id: "subject-mat",
        teacher_id: "teacher-1",
        starts_on: "2026-03-02",
      });
    });

    test("solo ofrece reasignar las asignaciones vigentes", async () => {
      academicsServiceMock.listTeachingAssignmentHistory.mockResolvedValue(
        paged([{ ...ASSIGNMENT, ends_on: "2026-06-30" }])
      );
      renderWithRouter(<TeachingAssignmentsPage />);

      expect(await screen.findByText("Cerrada")).toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: "Reasignar a otro docente" })
      ).not.toBeInTheDocument();
    });
  });
});
