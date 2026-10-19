import { configure, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useLocation } from "react-router-dom";
import { vi } from "vitest";

import { AttendancePage } from "@attendance/AttendancePage.jsx";
import { formatRemaining } from "@attendance/studentSearch.js";
import { CAMERA_ERROR, CameraAccessError } from "@shared/platform/camera.js";
import { todayInputValue } from "@shared/utils/format.js";
import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";
import { selectOption } from "./helpers/selectOption.jsx";

// Cada pestaña, bandeja y formulario se descarga diferido: bajo la carga de la
// suite completa el primer chunk puede tardar más que el segundo por omisión.
configure({ asyncUtilTimeout: 5000 });

const attendanceServiceMock = vi.hoisted(() => ({
  listJornadaParameters: vi.fn(),
  createJornadaParameters: vi.fn(),
  listEvents: vi.fn(),
  createEvent: vi.fn(),
  eventResolution: vi.fn(),
  dayStatus: vi.fn(),
  closeJornada: vi.fn(),
  previewSectionClosure: vi.fn(),
  closeSection: vi.fn(),
  listAlerts: vi.fn(),
  listControlPoints: vi.fn(),
  recordScan: vi.fn(),
  listPresence: vi.fn(),
  attendancePercentage: vi.fn(),
  listManualReasons: vi.fn(),
  currentCaptureBatch: vi.fn(),
  openCaptureBatch: vi.fn(),
  confirmCaptureBatch: vi.fn(),
  coverageRatio: vi.fn(),
}));

const studentsServiceMock = vi.hoisted(() => ({ listPage: vi.fn() }));
const cyclesServiceMock = vi.hoisted(() => ({ list: vi.fn() }));
const createCameraSessionMock = vi.hoisted(() => vi.fn());

vi.mock("@attendance/attendanceService.js", async () => {
  const actual = await vi.importActual("@attendance/attendanceService.js");
  return { ...actual, attendanceService: attendanceServiceMock };
});

// RNF-USA-001: el chequeo preventivo de cámara corre al montar la página; sin
// doble se dispararía una petición real de getUserMedia en jsdom.
vi.mock("@shared/platform/camera.js", async () => {
  const actual = await vi.importActual("@shared/platform/camera.js");
  return { ...actual, createCameraSession: createCameraSessionMock };
});

vi.mock("@students/studentsService.js", async () => {
  const actual = await vi.importActual("@students/studentsService.js");
  return { ...actual, studentsService: studentsServiceMock };
});

vi.mock("@cycles/cyclesService.js", async () => {
  const actual = await vi.importActual("@cycles/cyclesService.js");
  return { ...actual, cyclesService: cyclesServiceMock };
});

vi.mock("@academics/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});

import {
  academicsServiceMock,
  resetAcademicsServiceMock,
} from "./mocks/academicsService.js";

const ALL_ATTENDANCE = [
  "attendance.scan",
  "attendance.record_entry",
  "attendance.record_exit",
  "attendance.record_manual",
  "attendance.declared_close",
  "attendance.jornada.configure",
  "attendance.credential.issue",
  "attendance.justification.request",
  "attendance.justification.resolve",
  "attendance.permit.request",
  "attendance.permit.resolve",
  "student.view_basic",
];
const OPERATOR = sessionUser(ALL_ATTENDANCE);

const paged = (results) => ({ count: results.length, results });

const CAMPUS = { public_id: "campus-1", name: "Sede Central" };
const SHIFT = {
  public_id: "shift-1",
  name: "Matutina",
  code: "MAT",
  campus: CAMPUS,
};
const STUDENT = {
  public_id: "student-1",
  student_code: "EST-1",
  person: { first_name: "Luis", last_name: "Perez" },
};
const STUDENT_REF = {
  public_id: "student-1",
  student_code: "EST-1",
  full_name: "Luis Perez",
};
const SECTION = {
  public_id: "section-1",
  name: "A",
  capacity: 30,
  academic_cycle_id: "cycle-1",
  grade: { public_id: "grade-1", name: "Primero Basico" },
  shift: { public_id: SHIFT.public_id, name: "Matutina" },
};
const CONTROL_POINT = {
  public_id: "cp-1",
  name: "Porton principal",
  code: "PP-1",
  campus_id: "campus-1",
  is_active: true,
};
const OPEN_BATCH = {
  public_id: "batch-1",
  status: "open",
  confirmed_at: null,
  expires_at: new Date(Date.now() + 65 * 60 * 1000).toISOString(),
  created_at: "2026-10-19T13:00:00Z",
};
const BATCH_EVENT = {
  public_id: "ev-1",
  student_id: "student-1",
  student: STUDENT_REF,
  shift_id: "shift-1",
  event_date: "2026-10-19",
  movement_type: "entry",
  origin: "scan",
  captured_at: "2026-10-19T13:05:00Z",
  is_active: true,
};

function LocationProbe() {
  return <output data-testid="location">{useLocation().search}</output>;
}

function renderPage(route = "/app/asistencia", user = OPERATOR) {
  return renderWithSession(
    <>
      <AttendancePage />
      <LocationProbe />
    </>,
    { user, route }
  );
}

beforeEach(() => {
  Object.values(attendanceServiceMock).forEach((mock) => mock.mockReset());
  attendanceServiceMock.listEvents.mockResolvedValue(paged([]));
  attendanceServiceMock.listAlerts.mockResolvedValue(paged([]));
  attendanceServiceMock.listJornadaParameters.mockResolvedValue(paged([]));
  attendanceServiceMock.listControlPoints.mockResolvedValue(
    paged([CONTROL_POINT])
  );
  attendanceServiceMock.currentCaptureBatch.mockResolvedValue({
    capture_batch: null,
    events: [],
  });
  attendanceServiceMock.listManualReasons.mockResolvedValue(
    paged([{ public_id: "reason-1", name: "Lector sin conexión" }])
  );

  resetAcademicsServiceMock();
  academicsServiceMock.listCampuses.mockResolvedValue(paged([CAMPUS]));
  academicsServiceMock.listCampusShifts.mockResolvedValue(paged([SHIFT]));
  academicsServiceMock.listSections.mockResolvedValue(paged([SECTION]));
  studentsServiceMock.listPage.mockReset().mockResolvedValue(paged([STUDENT]));
  cyclesServiceMock.list.mockReset().mockResolvedValue(
    paged([
      {
        public_id: "cycle-1",
        name: "Ciclo 2026",
        year: 2026,
        status: "active",
      },
    ])
  );

  createCameraSessionMock
    .mockReset()
    .mockResolvedValue({ stream: null, stop: vi.fn() });
});

/** Busca un estudiante en el servidor y lo elige. */
async function pickStudent(user, scope = screen) {
  await user.type(scope.getByRole("combobox", { name: /Estudiante/ }), "Lu");
  await user.click(
    await screen.findByRole("option", { name: "Luis Perez · EST-1" })
  );
}

async function openScanWindow(user) {
  await user.click(
    await screen.findByRole("button", { name: "Registrar por escaneo" })
  );
  return screen.findByRole("dialog", { name: "Registrar por escaneo" });
}

async function scan(user, dialog, code = "EST-001") {
  await user.type(within(dialog).getByLabelText(/^Código de estudiante/), code);
  await selectOption(user, /^Punto de control/, /Porton principal/, dialog);
  await selectOption(user, /^Jornada/, /Matutina/, dialog);
  await user.click(within(dialog).getByRole("button", { name: "Registrar" }));
}

const created = (overrides = {}) => [
  {
    client_event_id: "any",
    outcome: "created",
    event: { origin: "scan", movement_type: "entry" },
    duplicate_of: null,
    reason: "",
    ...overrides,
  },
];

describe("Asistencia — pestañas por permiso (AS6)", () => {
  test("con todos los permisos muestra las seis pestañas y abre en Hoy", async () => {
    renderPage();

    const tabs = screen.getByRole("tablist", {
      name: "Partes de la asistencia",
    });
    expect(
      within(tabs)
        .getAllByRole("tab")
        .map((tab) => tab.textContent)
    ).toEqual([
      "Hoy",
      "Movimientos",
      "Cierres",
      "Justificaciones y permisos",
      "Carnés",
      "Configuración",
    ]);
    expect(
      await screen.findByRole("heading", { name: "Turno de captura" })
    ).toBeInTheDocument();
    // Las demás pestañas no se piden hasta abrirlas.
    expect(attendanceServiceMock.listEvents).not.toHaveBeenCalled();
  });

  test("cambiar de pestaña queda en la URL", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("tab", { name: "Movimientos" }));

    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent(
        "tab=movimientos"
      )
    );
    expect(
      await screen.findByRole("heading", { name: "Movimientos" })
    ).toBeInTheDocument();
  });

  test("quien solo presenta justificaciones ve solo su pestaña y no se le pide la cámara", async () => {
    renderPage(
      "/app/asistencia",
      sessionUser(["attendance.justification.request"])
    );

    const tabs = screen.getByRole("tablist", {
      name: "Partes de la asistencia",
    });
    expect(
      within(tabs)
        .getAllByRole("tab")
        .map((tab) => tab.textContent)
    ).toEqual(["Justificaciones y permisos"]);
    expect(createCameraSessionMock).not.toHaveBeenCalled();
  });

  test("sin permisos de asistencia lo dice en vez de mostrar pestañas vacías", () => {
    renderPage("/app/asistencia", sessionUser([]));

    expect(
      screen.getByText(/Su cuenta no tiene permisos de asistencia/)
    ).toBeInTheDocument();
    expect(screen.queryByRole("tablist")).not.toBeInTheDocument();
  });
});

describe("Asistencia → Hoy: turno de captura (AS1)", () => {
  test("formatRemaining muestra minutos o horas", () => {
    expect(formatRemaining(4 * 60 * 1000 + 9000)).toBe("4:09");
    expect(formatRemaining((65 * 60 + 9) * 1000)).toBe("1:05:09");
    expect(formatRemaining(-5000)).toBe("0:00");
  });

  test("sin turno ofrece abrirlo y luego muestra su vencimiento", async () => {
    attendanceServiceMock.currentCaptureBatch
      .mockResolvedValueOnce({ capture_batch: null, events: [] })
      .mockResolvedValue({ capture_batch: OPEN_BATCH, events: [BATCH_EVENT] });
    attendanceServiceMock.openCaptureBatch.mockResolvedValue(OPEN_BATCH);
    const user = userEvent.setup();
    renderPage();

    expect(
      await screen.findByText(/No hay un turno de captura abierto/)
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Abrir turno" }));

    expect(attendanceServiceMock.openCaptureBatch).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("Abierto")).toBeInTheDocument();
    expect(screen.getByText(/^Quedan \d+:\d{2}:\d{2}$/)).toBeInTheDocument();
    expect(screen.getByText("1 movimiento capturado")).toBeInTheDocument();
    // La fila del turno trae el nombre del estudiante, no su UUID.
    expect(screen.getByText("Luis Perez")).toBeInTheDocument();
  });

  test("el escaneo con turno abierto envía capture_batch_id", async () => {
    attendanceServiceMock.currentCaptureBatch.mockResolvedValue({
      capture_batch: OPEN_BATCH,
      events: [],
    });
    attendanceServiceMock.recordScan.mockResolvedValue(created());
    const user = userEvent.setup();
    renderPage();
    await screen.findByText("Abierto");

    const dialog = await openScanWindow(user);
    await scan(user, dialog);

    await waitFor(() =>
      expect(attendanceServiceMock.recordScan).toHaveBeenCalledTimes(1)
    );
    const payload = attendanceServiceMock.recordScan.mock.calls[0][0];
    expect(payload.capture_batch_id).toBe("batch-1");
    expect(payload.items[0]).toEqual(
      expect.objectContaining({
        student_code: "EST-001",
        control_point_id: "cp-1",
        shift_id: "shift-1",
        movement_type: "entry",
      })
    );
    expect(await within(dialog).findByText("Registrado")).toBeInTheDocument();
  });

  test("sin turno el escaneo no lleva capture_batch_id", async () => {
    attendanceServiceMock.recordScan.mockResolvedValue(created());
    const user = userEvent.setup();
    renderPage();
    await screen.findByText(/No hay un turno de captura abierto/);

    const dialog = await openScanWindow(user);
    await scan(user, dialog);

    await waitFor(() =>
      expect(attendanceServiceMock.recordScan).toHaveBeenCalledTimes(1)
    );
    expect(
      attendanceServiceMock.recordScan.mock.calls[0][0]
    ).not.toHaveProperty("capture_batch_id");
  });

  test("confirmar el turno pide confirmación y lo cierra", async () => {
    attendanceServiceMock.currentCaptureBatch.mockResolvedValue({
      capture_batch: OPEN_BATCH,
      events: [BATCH_EVENT],
    });
    attendanceServiceMock.confirmCaptureBatch.mockResolvedValue({
      ...OPEN_BATCH,
      status: "confirmed",
    });
    const user = userEvent.setup();
    renderPage();

    await user.click(
      await screen.findByRole("button", { name: "Confirmar turno" })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Confirmar turno de captura",
    });
    expect(attendanceServiceMock.confirmCaptureBatch).not.toHaveBeenCalled();
    await user.click(
      within(dialog).getByRole("button", { name: "Confirmar turno" })
    );

    await waitFor(() =>
      expect(attendanceServiceMock.confirmCaptureBatch).toHaveBeenCalledWith(
        "batch-1"
      )
    );
  });

  test("un turno vencido se muestra vencido y ofrece abrir otro", async () => {
    attendanceServiceMock.currentCaptureBatch.mockResolvedValue({
      capture_batch: {
        ...OPEN_BATCH,
        expires_at: new Date(Date.now() - 1000).toISOString(),
      },
      events: [],
    });
    renderPage();

    expect(await screen.findByText("Vencido")).toBeInTheDocument();
    expect(
      screen.getByText(
        "El turno de captura venció y se cerró. Abra un turno nuevo para seguir registrando."
      )
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Abrir turno" })
    ).toBeInTheDocument();
  });
});

describe("Asistencia → Hoy: captura por escaneo", () => {
  test("informa la hora del movimiento duplicado sin crear uno nuevo", async () => {
    attendanceServiceMock.recordScan.mockResolvedValue(
      created({
        outcome: "duplicate_suppressed",
        event: null,
        duplicate_of: {
          movement_type: "entry",
          captured_at: "2026-08-19T13:00:00Z",
        },
      })
    );
    const user = userEvent.setup();
    renderPage();
    const dialog = await openScanWindow(user);
    await scan(user, dialog, "EST-002");

    expect(
      await within(dialog).findByText("Ya estaba registrado")
    ).toBeInTheDocument();
    expect(within(dialog).getByText(/ya registrado a las/)).toBeInTheDocument();
  });

  test.each([
    [
      "non_school_day",
      "El escaneo cae en un día no lectivo de la jornada y no se registró.",
    ],
    [
      "outside_operating_window",
      "El escaneo está fuera del horario de recepción de la jornada (antes de la apertura o después del cierre) y no se registró.",
    ],
    [
      "capture_batch_expired",
      "El turno de captura venció y se cerró. Abra un turno nuevo para seguir registrando.",
    ],
  ])(
    "explica en español el rechazo %s (RF-JOR-001 / RF-AUT-005)",
    async (reasonCode, message) => {
      attendanceServiceMock.recordScan.mockResolvedValue(
        created({
          outcome: "rejected",
          event: null,
          reason: "Detalle del servidor.",
          reason_code: reasonCode,
        })
      );
      const user = userEvent.setup();
      renderPage();
      const dialog = await openScanWindow(user);
      await scan(user, dialog, "EST-003");

      expect(await within(dialog).findByText("Rechazado")).toBeInTheDocument();
      expect(within(dialog).getByText(message)).toBeInTheDocument();
      expect(
        within(dialog).getByText("Detalle del servidor.")
      ).toBeInTheDocument();
    }
  );

  test("reintenta con el mismo client_event_id tras un fallo de red", async () => {
    attendanceServiceMock.recordScan
      .mockRejectedValueOnce(new Error("La red falló."))
      .mockResolvedValueOnce(created({ event: {} }));
    const user = userEvent.setup();
    renderPage();
    const dialog = await openScanWindow(user);

    await scan(user, dialog, "EST-003");
    expect(
      await within(dialog).findByText("La red falló.")
    ).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Registrar" }));
    await waitFor(() =>
      expect(attendanceServiceMock.recordScan).toHaveBeenCalledTimes(2)
    );

    const [first, second] = attendanceServiceMock.recordScan.mock.calls.map(
      ([payload]) => payload.items[0].client_event_id
    );
    expect(second).toBe(first);
  });
});

describe("Asistencia → Hoy: consultas", () => {
  test("el porcentaje busca al estudiante en el servidor", async () => {
    attendanceServiceMock.attendancePercentage.mockResolvedValue({
      elapsed_school_days: 10,
      present_days: 8,
      late_days: 1,
      percentage: 90,
    });
    const user = userEvent.setup();
    renderPage();

    const card = (
      await screen.findByRole("heading", { name: "Porcentaje de asistencia" })
    ).closest("section");
    const scoped = within(card);
    await pickStudent(user, scoped);
    await user.click(scoped.getByLabelText(/^Jornada/));
    await user.click(
      await screen.findByRole("option", { name: "Matutina · Sede Central" })
    );
    await user.click(scoped.getByRole("button", { name: /Consultar/ }));

    expect(studentsServiceMock.listPage).toHaveBeenCalledWith({
      search: "Lu",
    });
    expect(attendanceServiceMock.attendancePercentage).toHaveBeenCalledWith(
      expect.objectContaining({ student_id: "student-1", shift_id: "shift-1" })
    );
    expect(await scoped.findByText("90%")).toBeInTheDocument();
    expect(
      scoped.getByText("9 de 10 días lectivos transcurridos")
    ).toBeInTheDocument();
  });

  test("el estado del día arranca en hoy, exige los tres datos y muestra la etiqueta", async () => {
    attendanceServiceMock.dayStatus.mockResolvedValue({
      status: "ausente_pendiente_justificar",
      entry_event: null,
    });
    const user = userEvent.setup();
    renderPage();

    const card = (
      await screen.findByRole("heading", { name: "Estado del día" })
    ).closest("section");
    const scoped = within(card);
    const dateInput = scoped.getByLabelText(/^Fecha/);
    expect(dateInput).toHaveValue(todayInputValue());
    expect(scoped.getByRole("button", { name: /Consultar/ })).toBeDisabled();

    await pickStudent(user, scoped);
    await user.click(scoped.getByRole("combobox", { name: /Jornada/ }));
    await user.click(
      await screen.findByRole("option", { name: "Matutina · Sede Central" })
    );
    await user.clear(dateInput);
    // El endpoint exige los tres: con dos devolvería 400.
    expect(scoped.getByRole("button", { name: /Consultar/ })).toBeDisabled();

    await user.click(
      scoped.getByRole("button", { name: "Usar la fecha de hoy" })
    );
    expect(dateInput).toHaveValue(todayInputValue());
    await user.click(scoped.getByRole("button", { name: /Consultar/ }));

    expect(
      await scoped.findByText("Ausente pendiente de justificar")
    ).toBeInTheDocument();
  });

  test("presencia: no consulta sin jornada y nombra a los presentes", async () => {
    attendanceServiceMock.listPresence.mockResolvedValue(
      paged([
        {
          student_id: "student-1",
          student: STUDENT_REF,
          section_id: "section-1",
          entry_event: { captured_at: "2026-08-19T13:00:00Z" },
        },
      ])
    );
    const user = userEvent.setup();
    renderPage();

    await user.click(
      await screen.findByRole("button", { name: "Presencia en tiempo real" })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Presencia en tiempo real",
    });
    expect(
      within(dialog).getByText(
        "Elija la jornada para consultar quién está presente."
      )
    ).toBeInTheDocument();
    expect(attendanceServiceMock.listPresence).not.toHaveBeenCalled();

    await selectOption(user, /^Jornada/, /Matutina/, dialog);
    await user.click(within(dialog).getByRole("button", { name: "Buscar" }));

    expect(await within(dialog).findByText("Luis Perez")).toBeInTheDocument();
    expect(within(dialog).getByText("Primero Basico A")).toBeInTheDocument();
    // Ya no se descarga el padrón de estudiantes para nombrar las filas.
    expect(studentsServiceMock.listPage).not.toHaveBeenCalled();
  });
});

describe("Asistencia → Movimientos (AS5)", () => {
  test("lista movimientos y alertas con el nombre de la fila, sin padrón", async () => {
    attendanceServiceMock.listEvents.mockResolvedValue(paged([BATCH_EVENT]));
    renderPage("/app/asistencia?tab=movimientos");

    expect(
      await screen.findByRole("heading", { name: "Movimientos" })
    ).toBeInTheDocument();
    expect(await screen.findByText("Luis Perez")).toBeInTheDocument();
    expect(
      screen.getByText("Sin alertas de asistencia registradas.")
    ).toBeInTheDocument();
    expect(studentsServiceMock.listPage).not.toHaveBeenCalled();
  });

  test("filtra los movimientos por estudiante buscado en el servidor", async () => {
    const user = userEvent.setup();
    renderPage("/app/asistencia?tab=movimientos");
    const card = (
      await screen.findByRole("heading", { name: "Movimientos" })
    ).closest("section");

    await pickStudent(user, within(card));

    await waitFor(() =>
      expect(attendanceServiceMock.listEvents).toHaveBeenLastCalledWith(
        expect.objectContaining({ student_id: "student-1" })
      )
    );
    expect(screen.getByTestId("location")).toHaveTextContent(
      "mov_student_id=student-1"
    );
  });

  test("el registro manual exige un motivo vigente y lo envía", async () => {
    attendanceServiceMock.createEvent.mockResolvedValue({});
    const user = userEvent.setup();
    renderPage("/app/asistencia?tab=movimientos");

    await user.click(
      await screen.findByRole("button", { name: "Registrar movimiento" })
    );
    const form = await screen.findByRole("dialog", {
      name: "Nuevo movimiento de asistencia",
    });
    await pickStudent(user, within(form));
    await selectOption(user, /^Jornada/, /Matutina/, form);

    // Sin motivo el formulario no se envía: era el 400 de cada registro manual.
    await user.click(
      within(form).getByRole("button", { name: "Registrar movimiento" })
    );
    expect(
      await within(form).findByText("Complete el campo motivo.")
    ).toBeInTheDocument();
    expect(attendanceServiceMock.createEvent).not.toHaveBeenCalled();

    await selectOption(user, /^Motivo/, "Lector sin conexión", form);
    await user.click(
      within(form).getByRole("button", { name: "Registrar movimiento" })
    );

    await waitFor(() =>
      expect(attendanceServiceMock.createEvent).toHaveBeenCalledWith({
        student_id: "student-1",
        shift_id: "shift-1",
        event_date: todayInputValue(),
        movement_type: "entry",
        origin: "manual",
        manual_reason_id: "reason-1",
        captured_at: todayInputValue(),
      })
    );
  });

  test("un origen distinto de manual no pide ni envía motivo", async () => {
    attendanceServiceMock.createEvent.mockResolvedValue({});
    const user = userEvent.setup();
    renderPage("/app/asistencia?tab=movimientos");

    await user.click(
      await screen.findByRole("button", { name: "Registrar movimiento" })
    );
    const form = await screen.findByRole("dialog", {
      name: "Nuevo movimiento de asistencia",
    });
    await pickStudent(user, within(form));
    await selectOption(user, /^Jornada/, /Matutina/, form);
    await selectOption(user, /^Origen/, "Lectura", form);

    expect(within(form).queryByLabelText(/^Motivo/)).not.toBeInTheDocument();
    await user.click(
      within(form).getByRole("button", { name: "Registrar movimiento" })
    );
    await waitFor(() =>
      expect(attendanceServiceMock.createEvent).toHaveBeenCalledTimes(1)
    );
    expect(
      attendanceServiceMock.createEvent.mock.calls[0][0]
    ).not.toHaveProperty("manual_reason_id");
  });

  test("solo ofrece los orígenes que la cuenta puede registrar", async () => {
    const user = userEvent.setup();
    renderPage(
      "/app/asistencia?tab=movimientos",
      sessionUser([
        "student.view_basic",
        "attendance.record_manual",
        "attendance.record_entry",
      ])
    );

    await user.click(
      await screen.findByRole("button", { name: "Registrar movimiento" })
    );
    const form = await screen.findByRole("dialog", {
      name: "Nuevo movimiento de asistencia",
    });
    await user.click(within(form).getByLabelText(/^Origen/));
    const listbox = await screen.findByRole("listbox");
    const offered = within(listbox)
      .getAllByRole("option")
      .map((option) => option.textContent);
    expect(offered).toContain("Manual");
    expect(offered).not.toContain("Lectura");
    expect(offered).not.toContain("Declarada");
  });
});

describe("Asistencia → Cierres (AS5)", () => {
  test("el cierre por cobertura pide una segunda confirmación", async () => {
    const preview = {
      section_id: "section-1",
      grade_name: "Primero Basico",
      event_date: "2026-09-05",
      included: [{ student_id: "student-1" }],
      omitted: [],
      is_covering: false,
      confirmation_required: false,
    };
    attendanceServiceMock.previewSectionClosure.mockResolvedValue(preview);
    attendanceServiceMock.closeSection
      .mockResolvedValueOnce({
        ...preview,
        is_covering: true,
        confirmation_required: true,
      })
      .mockResolvedValueOnce({ ...preview, is_covering: true });
    const user = userEvent.setup();
    renderPage("/app/asistencia?tab=cierres");

    await user.click(
      await screen.findByRole("button", { name: "Cerrar sección" })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Cierre declarado por sección",
    });
    await selectOption(user, /^Sección/, /Primero Basico A/, dialog);
    await user.click(
      within(dialog).getByRole("button", { name: "Previsualizar cierre" })
    );
    expect(await within(dialog).findByText("1 por cerrar")).toBeInTheDocument();

    await user.click(
      within(dialog).getByRole("button", { name: "Declarar cierre" })
    );
    const confirmation = await screen.findByRole("dialog", {
      name: "Confirmar cierre por cobertura",
    });
    expect(
      within(confirmation).getByText(/Actuará como docente de cobertura/)
    ).toBeInTheDocument();
    await user.click(
      within(confirmation).getByRole("button", { name: "Confirmar cierre" })
    );

    await waitFor(() =>
      expect(attendanceServiceMock.closeSection).toHaveBeenLastCalledWith({
        section_id: "section-1",
        event_date: expect.any(String),
        confirmed: true,
      })
    );
    expect(
      await within(dialog).findByText(
        "El cierre se registró y quedó en la bitácora de auditoría."
      )
    ).toBeInTheDocument();
  });

  test("abrir y cerrar el cierre de sección no ejecuta operaciones", async () => {
    const user = userEvent.setup();
    renderPage("/app/asistencia?tab=cierres");

    await user.click(
      await screen.findByRole("button", { name: "Cerrar sección" })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Cierre declarado por sección",
    });
    await user.click(
      within(dialog).getAllByRole("button", { name: "Cerrar" })[0]
    );
    await waitFor(() => expect(dialog).not.toBeInTheDocument());
    expect(attendanceServiceMock.previewSectionClosure).not.toHaveBeenCalled();
    expect(attendanceServiceMock.closeSection).not.toHaveBeenCalled();
  });

  test("cierra la jornada tras confirmar y resume el resultado", async () => {
    attendanceServiceMock.closeJornada.mockResolvedValue({
      shift_id: "shift-1",
      event_date: "2026-10-19",
      statuses: [{}, {}, {}],
      alerts: [{}],
    });
    const user = userEvent.setup();
    renderPage("/app/asistencia?tab=cierres");
    const card = (
      await screen.findByRole("heading", { name: "Cierre de jornada" })
    ).closest("section");

    await selectOption(user, /^Jornada/, /Matutina/, card);
    await user.click(
      within(card).getByRole("button", { name: "Cerrar jornada" })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Cerrar jornada",
    });
    await user.click(
      within(dialog).getByRole("button", { name: "Cerrar jornada" })
    );

    await waitFor(() =>
      expect(attendanceServiceMock.closeJornada).toHaveBeenCalledWith({
        shift_id: "shift-1",
        event_date: todayInputValue(),
      })
    );
    expect(
      await within(card).findByText(
        /3 estudiantes con estado calculado y 1 alertas emitidas/
      )
    ).toBeInTheDocument();
  });

  test("consulta la razón de cobertura con filtros opcionales", async () => {
    attendanceServiceMock.coverageRatio.mockResolvedValue({
      total_closures: 4,
      covering_closures: 1,
      coverage_ratio: 0.25,
    });
    const user = userEvent.setup();
    renderPage("/app/asistencia?tab=cierres");
    const card = (
      await screen.findByRole("heading", {
        name: "Razón de cobertura de cierres",
      })
    ).closest("section");

    await selectOption(user, /^Sección/, /Primero Basico A/, card);
    await user.click(within(card).getByRole("button", { name: "Consultar" }));

    await waitFor(() =>
      expect(attendanceServiceMock.coverageRatio).toHaveBeenCalledWith({
        section_id: "section-1",
        date_from: "",
        date_to: "",
      })
    );
    expect(await within(card).findByText("25 %")).toBeInTheDocument();
    expect(
      within(card).getByText("1 de 4 cierres declarados por cobertura")
    ).toBeInTheDocument();
  });

  test("sin configurar la jornada solo se ve el cierre de sección", async () => {
    renderPage(
      "/app/asistencia?tab=cierres",
      sessionUser(["attendance.declared_close", "attendance.record_exit"])
    );

    expect(
      await screen.findByRole("button", { name: "Cerrar sección" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Cierre de jornada" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Razón de cobertura de cierres" })
    ).not.toBeInTheDocument();
  });
});

describe("Asistencia → Configuración", () => {
  test("abre la vista previa de cámara sin registrar movimientos", async () => {
    const user = userEvent.setup();
    renderPage("/app/asistencia?tab=configuracion");

    await user.click(
      await screen.findByRole("button", { name: "Abrir cámara" })
    );

    expect(
      await screen.findByRole("dialog", { name: "Vista previa de camara" })
    ).toBeInTheDocument();
    expect(attendanceServiceMock.createEvent).not.toHaveBeenCalled();
  });

  test("registra parámetros con los días lectivos como lista", async () => {
    attendanceServiceMock.createJornadaParameters.mockResolvedValue({});
    const user = userEvent.setup();
    renderPage("/app/asistencia?tab=configuracion");

    await user.click(
      await screen.findByRole("button", { name: "Nuevos parámetros" })
    );
    const form = await screen.findByRole("dialog", {
      name: "Nuevos parámetros de jornada",
    });
    await selectOption(user, /^Jornada/, /Matutina/, form);
    await selectOption(user, /^Ciclo escolar/, /Ciclo 2026/, form);
    await user.type(
      within(form).getByLabelText(/^Hora límite de entrada/),
      "07:00"
    );
    await user.type(within(form).getByLabelText(/^Hora de cierre/), "13:00");
    await user.type(
      within(form).getByLabelText(/^Vigente desde/),
      "2026-01-15"
    );
    await user.click(
      within(form).getByRole("button", { name: "Registrar parámetros" })
    );

    await waitFor(() =>
      expect(
        attendanceServiceMock.createJornadaParameters
      ).toHaveBeenCalledWith(
        expect.objectContaining({
          shift_id: "shift-1",
          academic_cycle_id: "cycle-1",
          entry_limit_time: "07:00",
          closing_time: "13:00",
          school_days: [1, 2, 3, 4, 5],
        })
      )
    );
    expect(
      attendanceServiceMock.createJornadaParameters.mock.calls[0][0]
    ).not.toHaveProperty("opening_time");
  });
});

describe("Asistencia — verificación preventiva de cámara (RNF-USA-001)", () => {
  test("camino feliz: el permiso se verifica al entrar y no muestra aviso", async () => {
    const stop = vi.fn();
    createCameraSessionMock.mockResolvedValue({ stream: null, stop });

    renderPage();

    await waitFor(() => expect(stop).toHaveBeenCalled());
    expect(
      screen.queryByText(/No se pudo acceder a la camara/)
    ).not.toBeInTheDocument();
  });

  test("rechazo por autorización: informa sin bloquear el resto de la página", async () => {
    createCameraSessionMock.mockRejectedValue(
      new CameraAccessError(CAMERA_ERROR.permissionDenied)
    );
    const user = userEvent.setup();
    renderPage();

    expect(
      await screen.findByText(
        "No se pudo acceder a la camara. Habilita el permiso en el navegador y vuelve a intentarlo."
      )
    ).toBeInTheDocument();
    // El aviso no bloquea: el operador sigue pudiendo escanear.
    await openScanWindow(user);
  });
});

describe("Asistencia — sin persistencia local de datos de menores (RNF-PRI-003)", () => {
  // Lo único que la aplicación puede dejar en el navegador es la preferencia
  // de tema de MUI; ningún dato del estudiante.
  const ALLOWED_KEYS = ["mui-mode"];

  test("escanear y consultar presencia no deja datos del estudiante en el dispositivo", async () => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    const openDatabase = vi.fn();
    vi.stubGlobal("indexedDB", { open: openDatabase });
    attendanceServiceMock.recordScan.mockResolvedValue(created());
    attendanceServiceMock.listPresence.mockResolvedValue(
      paged([
        {
          student_id: "student-1",
          student: STUDENT_REF,
          section_id: "section-1",
          entry_event: { captured_at: "2026-08-19T13:00:00Z" },
        },
      ])
    );
    const user = userEvent.setup();
    renderPage();

    const scanDialog = await openScanWindow(user);
    await scan(user, scanDialog, "EST-1");
    expect(
      await within(scanDialog).findByText("Registrado")
    ).toBeInTheDocument();
    await user.click(
      within(scanDialog).getAllByRole("button", { name: "Cerrar" })[0]
    );
    await waitFor(() =>
      expect(
        screen.queryByRole("dialog", { name: "Registrar por escaneo" })
      ).not.toBeInTheDocument()
    );

    await user.click(
      screen.getByRole("button", { name: "Presencia en tiempo real" })
    );
    const presenceDialog = await screen.findByRole("dialog", {
      name: "Presencia en tiempo real",
    });
    await selectOption(user, /^Jornada/, /Matutina/, presenceDialog);
    await user.click(
      within(presenceDialog).getByRole("button", { name: "Buscar" })
    );
    expect(
      await within(presenceDialog).findByText("Luis Perez")
    ).toBeInTheDocument();

    for (const storage of [window.localStorage, window.sessionStorage]) {
      for (const key of Object.keys(storage)) {
        expect(ALLOWED_KEYS).toContain(key);
        expect(storage.getItem(key)).not.toMatch(/EST-1|Luis|Perez|student-1/);
      }
    }
    expect(openDatabase).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
