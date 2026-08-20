import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { AttendancePage } from "@attendance/AttendancePage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import { selectOption } from "./helpers/selectOption.jsx";

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

const studentsServiceMock = vi.hoisted(() => ({ listPage: vi.fn() }));

vi.mock("@attendance/attendanceService.js", async () => {
  const actual = await vi.importActual("@attendance/attendanceService.js");
  return { ...actual, attendanceService: attendanceServiceMock };
});

// Los selectores de jornada, grado, seccion y estudiante leen los catalogos, y
// sin doble irian a la red: en jsdom eso queda como un catalogo vacio y ninguna
// opcion que elegir.
vi.mock("@students/studentsService.js", async () => {
  const actual = await vi.importActual("@students/studentsService.js");
  return { ...actual, studentsService: studentsServiceMock };
});

vi.mock("@academics/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});

import {
  academicsServiceMock,
  resetAcademicsServiceMock,
} from "./mocks/academicsService.js";

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

beforeEach(() => {
  Object.values(attendanceServiceMock).forEach((mock) => mock.mockReset());
  attendanceServiceMock.listEvents.mockResolvedValue(paged([]));
  attendanceServiceMock.listAlerts.mockResolvedValue(paged([]));
  attendanceServiceMock.listControlPoints.mockResolvedValue(
    paged([CONTROL_POINT])
  );

  resetAcademicsServiceMock();
  academicsServiceMock.listCampuses.mockResolvedValue(paged([CAMPUS]));
  academicsServiceMock.listCampusShifts.mockResolvedValue(paged([SHIFT]));
  academicsServiceMock.listSections.mockResolvedValue(paged([SECTION]));
  studentsServiceMock.listPage.mockReset().mockResolvedValue(paged([STUDENT]));
});

async function openScanWindow(user) {
  await user.click(
    screen.getByRole("button", { name: "Registrar por escaneo" })
  );
  return screen.findByRole("dialog", { name: "Registrar por escaneo" });
}

describe("AttendancePage — captura por escaneo", () => {
  test("registra un movimiento y muestra el resultado", async () => {
    attendanceServiceMock.recordScan.mockResolvedValue([
      {
        client_event_id: "any",
        outcome: "created",
        event: { origin: "scan", movement_type: "entry" },
        duplicate_of: null,
        reason: "",
      },
    ]);
    const user = userEvent.setup();
    renderWithRouter(<AttendancePage />);
    const dialog = await openScanWindow(user);

    await user.type(
      within(dialog).getByLabelText(/^Codigo de estudiante/),
      "EST-001"
    );
    await selectOption(user, /^Punto de control/, /Porton principal/, dialog);
    await selectOption(user, /^Jornada/, /Matutina/, dialog);
    await user.click(within(dialog).getByRole("button", { name: "Registrar" }));

    await waitFor(() =>
      expect(attendanceServiceMock.recordScan).toHaveBeenCalledTimes(1)
    );
    const payload = attendanceServiceMock.recordScan.mock.calls[0][0];
    expect(payload.items[0]).toEqual(
      expect.objectContaining({
        student_code: "EST-001",
        control_point_id: "cp-1",
        shift_id: "shift-1",
        movement_type: "entry",
      })
    );
    expect(payload.items[0].client_event_id).toEqual(expect.any(String));

    expect(await within(dialog).findByText("Registrado")).toBeInTheDocument();
  }, 10000);

  test("informa la hora del movimiento duplicado sin crear uno nuevo", async () => {
    attendanceServiceMock.recordScan.mockResolvedValue([
      {
        client_event_id: "any",
        outcome: "duplicate_suppressed",
        event: null,
        duplicate_of: {
          movement_type: "entry",
          captured_at: "2026-08-19T13:00:00Z",
        },
        reason: "",
      },
    ]);
    const user = userEvent.setup();
    renderWithRouter(<AttendancePage />);
    const dialog = await openScanWindow(user);

    await user.type(
      within(dialog).getByLabelText(/^Codigo de estudiante/),
      "EST-002"
    );
    await selectOption(user, /^Punto de control/, /Porton principal/, dialog);
    await selectOption(user, /^Jornada/, /Matutina/, dialog);
    await user.click(within(dialog).getByRole("button", { name: "Registrar" }));

    expect(
      await within(dialog).findByText("Ya estaba registrado")
    ).toBeInTheDocument();
    expect(within(dialog).getByText(/ya registrado a las/)).toBeInTheDocument();
  }, 10000);

  test("reintenta con el mismo client_event_id tras un fallo de red", async () => {
    attendanceServiceMock.recordScan
      .mockRejectedValueOnce(new Error("La red fallo."))
      .mockResolvedValueOnce([
        {
          client_event_id: "any",
          outcome: "created",
          event: {},
          duplicate_of: null,
          reason: "",
        },
      ]);
    const user = userEvent.setup();
    renderWithRouter(<AttendancePage />);
    const dialog = await openScanWindow(user);

    await user.type(
      within(dialog).getByLabelText(/^Codigo de estudiante/),
      "EST-003"
    );
    await selectOption(user, /^Punto de control/, /Porton principal/, dialog);
    await selectOption(user, /^Jornada/, /Matutina/, dialog);

    const submitButton = within(dialog).getByRole("button", {
      name: "Registrar",
    });
    await user.click(submitButton);
    expect(
      await within(dialog).findByText("La red fallo.")
    ).toBeInTheDocument();

    await user.click(submitButton);
    await waitFor(() =>
      expect(attendanceServiceMock.recordScan).toHaveBeenCalledTimes(2)
    );

    const firstId =
      attendanceServiceMock.recordScan.mock.calls[0][0].items[0]
        .client_event_id;
    const secondId =
      attendanceServiceMock.recordScan.mock.calls[1][0].items[0]
        .client_event_id;
    expect(secondId).toBe(firstId);
  }, 10000);
});

describe("AttendancePage — presencia en tiempo real", () => {
  test("no consulta hasta que se ingresa la jornada", async () => {
    const user = userEvent.setup();
    renderWithRouter(<AttendancePage />);

    await user.click(
      screen.getByRole("button", { name: "Presencia en tiempo real" })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Presencia en tiempo real",
    });

    expect(
      within(dialog).getByText(
        "Elija la jornada para consultar quien esta presente."
      )
    ).toBeInTheDocument();
    expect(attendanceServiceMock.listPresence).not.toHaveBeenCalled();
  }, 10000);

  test("lista a los estudiantes presentes tras buscar", async () => {
    attendanceServiceMock.listPresence.mockResolvedValue(
      paged([
        {
          student_id: "student-1",
          section_id: "section-1",
          entry_event: { captured_at: "2026-08-19T13:00:00Z" },
        },
      ])
    );
    const user = userEvent.setup();
    renderWithRouter(<AttendancePage />);

    await user.click(
      screen.getByRole("button", { name: "Presencia en tiempo real" })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Presencia en tiempo real",
    });
    await selectOption(user, /^Jornada/, /Matutina/, dialog);
    await user.click(within(dialog).getByRole("button", { name: "Buscar" }));

    await waitFor(() =>
      expect(attendanceServiceMock.listPresence).toHaveBeenCalledWith(
        expect.objectContaining({ shift_id: "shift-1" })
      )
    );
    // Nombres, no UUIDs: la tabla mostraba "student-1" y "section-1".
    expect(
      await within(dialog).findByText("Luis Perez · EST-1")
    ).toBeInTheDocument();
    expect(within(dialog).getByText("Primero Basico A")).toBeInTheDocument();
  }, 10000);
});

describe("AttendancePage — porcentaje de asistencia", () => {
  test("muestra el porcentaje consultado", async () => {
    attendanceServiceMock.attendancePercentage.mockResolvedValue({
      elapsed_school_days: 10,
      present_days: 8,
      late_days: 1,
      percentage: 90,
    });
    const user = userEvent.setup();
    renderWithRouter(<AttendancePage />);

    const card = screen
      .getByRole("heading", { name: "Porcentaje de asistencia" })
      .closest("section");
    const scoped = within(card);

    await user.click(scoped.getByLabelText(/^Estudiante/));
    await user.click(
      await screen.findByRole("option", { name: "Luis Perez · EST-1" })
    );
    await user.click(scoped.getByLabelText(/^Jornada/));
    await user.click(
      await screen.findByRole("option", { name: "Matutina · Sede Central" })
    );
    await user.click(scoped.getByRole("button", { name: /Consultar/ }));

    expect(await scoped.findByText("90%")).toBeInTheDocument();
    expect(
      scoped.getByText("9 de 10 dias lectivos transcurridos")
    ).toBeInTheDocument();
  }, 10000);
});
