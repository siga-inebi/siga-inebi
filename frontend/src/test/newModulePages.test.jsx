import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

const cyclesServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  create: vi.fn(),
  activate: vi.fn(),
  clone: vi.fn(),
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

    attendanceServiceMock.listEvents.mockReset().mockResolvedValue(paged([]));
    attendanceServiceMock.listAlerts.mockReset().mockResolvedValue(paged([]));
    attendanceServiceMock.listJornadaParameters
      .mockReset()
      .mockResolvedValue(paged([]));
    attendanceServiceMock.dayStatus
      .mockReset()
      .mockResolvedValue({ status: "presente", entry_event: null });

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
    test("muestra las matriculas vigentes", async () => {
      renderWithRouter(<EnrolmentsPage />);

      expect(
        await screen.findByRole("heading", { name: "Matriculas vigentes" })
      ).toBeInTheDocument();
      expect(screen.getByText("student-1")).toBeInTheDocument();
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
        screen.getByText(/escribe un ID de estudiante en el filtro/)
      ).toBeInTheDocument();
      expect(enrolmentsServiceMock.listHistory).not.toHaveBeenCalled();
    });

    test("abre el expediente documental de una matricula", async () => {
      const user = userEvent.setup();
      renderWithRouter(<EnrolmentsPage />);
      await screen.findByText("student-1");

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
      await screen.findByText("student-1");

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

    test("el estado del dia no consulta hasta tener los tres campos", async () => {
      const user = userEvent.setup();
      renderWithRouter(<AttendancePage />);

      expect(
        await screen.findByRole("heading", { name: "Estado del dia" })
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Consultar/ })).toBeDisabled();

      await user.type(screen.getByLabelText(/^ID de estudiante/), "student-1");
      await user.type(screen.getByLabelText(/^ID de jornada/), "shift-1");
      expect(screen.getByRole("button", { name: /Consultar/ })).toBeDisabled();
      expect(attendanceServiceMock.dayStatus).not.toHaveBeenCalled();
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
    test("lista el historial y distingue la vigencia", async () => {
      renderWithRouter(<TeachingAssignmentsPage />);

      expect(await screen.findByText("teacher-1")).toBeInTheDocument();
      expect(screen.getByText("Vigente")).toBeInTheDocument();
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
