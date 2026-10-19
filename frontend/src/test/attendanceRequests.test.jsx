import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useLocation } from "react-router-dom";
import { vi } from "vitest";

import { AttendancePage } from "@attendance/AttendancePage.jsx";
import { todayInputValue } from "@shared/utils/format.js";
import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";
import { selectOption } from "./helpers/selectOption.jsx";

const attendanceServiceMock = vi.hoisted(() => ({
  listJustifications: vi.fn(),
  getJustification: vi.fn(),
  createJustification: vi.fn(),
  resolveJustification: vi.fn(),
  listJustificationReasons: vi.fn(),
  getJustificationAttachment: vi.fn(),
  uploadJustificationAttachment: vi.fn(),
  listPermits: vi.fn(),
  getPermit: vi.fn(),
  createPermit: vi.fn(),
  resolvePermit: vi.fn(),
}));
const studentsServiceMock = vi.hoisted(() => ({ listPage: vi.fn() }));

vi.mock("@attendance/attendanceService.js", async () => {
  const actual = await vi.importActual("@attendance/attendanceService.js");
  return { ...actual, attendanceService: attendanceServiceMock };
});
vi.mock("@students/studentsService.js", async () => {
  const actual = await vi.importActual("@students/studentsService.js");
  return { ...actual, studentsService: studentsServiceMock };
});

const REQUEST = "attendance.justification.request";
const RESOLVE = "attendance.justification.resolve";
const PERMIT_REQUEST = "attendance.permit.request";
const PERMIT_RESOLVE = "attendance.permit.resolve";
const REVIEWER = sessionUser([
  REQUEST,
  RESOLVE,
  PERMIT_REQUEST,
  PERMIT_RESOLVE,
]);

const paged = (results) => ({ count: results.length, results });
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
const JUSTIFICATION = {
  public_id: "jus-1",
  student_id: "student-1",
  student: STUDENT_REF,
  absence_date: "2026-10-15",
  situation_type: "absence",
  situation_type_display: "Inasistencia",
  reason: "Cita médica",
  reason_catalog: { public_id: "r-1", name: "Salud" },
  status: "pending",
  status_display: "Pendiente",
  has_attachment: true,
  submitted_by: { public_id: "other-account", name: "Ana Encargada" },
  submitted_at: "2026-10-16T14:00:00Z",
  is_exception: false,
  exception_reason: "",
  resolved_by: null,
  resolved_at: null,
  resolution_comment: "",
};
const PERMIT = {
  public_id: "per-1",
  student_id: "student-1",
  student: STUDENT_REF,
  permit_type: "early_exit",
  permit_type_display: "Salida anticipada",
  permit_date: "2026-10-20",
  scheduled_time: "11:30:00",
  reason: "Consulta médica",
  status: "pending",
  status_display: "Pendiente",
  submitted_by: { public_id: "other-account", name: "Ana Encargada" },
  submitted_at: "2026-10-19T14:00:00Z",
  resolved_by: null,
  resolved_at: null,
  resolution_comment: "",
};

function LocationProbe() {
  return <output data-testid="location">{useLocation().search}</output>;
}

function renderRequests(query = "", user = REVIEWER) {
  return renderWithSession(
    <>
      <AttendancePage />
      <LocationProbe />
    </>,
    { user, route: `/app/asistencia?tab=solicitudes${query}` }
  );
}

beforeEach(() => {
  Object.values(attendanceServiceMock).forEach((mock) => mock.mockReset());
  attendanceServiceMock.listJustifications.mockResolvedValue(
    paged([JUSTIFICATION])
  );
  attendanceServiceMock.getJustification.mockResolvedValue(JUSTIFICATION);
  attendanceServiceMock.listJustificationReasons.mockResolvedValue(
    paged([{ public_id: "r-1", name: "Salud", code: "SAL" }])
  );
  attendanceServiceMock.listPermits.mockResolvedValue(paged([PERMIT]));
  attendanceServiceMock.getPermit.mockResolvedValue(PERMIT);
  studentsServiceMock.listPage.mockReset().mockResolvedValue(paged([STUDENT]));
});

async function pickStudent(user, scope) {
  await user.type(scope.getByRole("combobox", { name: /Estudiante/ }), "Lu");
  await user.click(
    await screen.findByRole("option", { name: "Luis Perez · EST-1" })
  );
}

describe("Justificaciones (AS3)", () => {
  test("la bandeja arranca en pendientes y nombra a cada estudiante", async () => {
    renderRequests();

    expect(await screen.findByText("Luis Perez")).toBeInTheDocument();
    expect(attendanceServiceMock.listJustifications).toHaveBeenCalledWith(
      expect.objectContaining({ status: "pending" })
    );
    const row = screen.getByText("Luis Perez").closest("tr");
    expect(within(row).getByText("Salud")).toBeInTheDocument();
    expect(within(row).getByText("Pendiente")).toBeInTheDocument();
    expect(within(row).getByText("Sí")).toBeInTheDocument();
  });

  test("«Todos» quita el filtro de estado y queda en la URL", async () => {
    const user = userEvent.setup();
    renderRequests();
    await screen.findByText("Luis Perez");

    await selectOption(user, /^Estado/, "Todos");

    await waitFor(() =>
      expect(attendanceServiceMock.listJustifications).toHaveBeenLastCalledWith(
        expect.not.objectContaining({ status: expect.anything() })
      )
    );
    expect(screen.getByTestId("location")).toHaveTextContent("jus_status=all");
  });

  test("las fechas filtran en el servidor", async () => {
    renderRequests("&jus_date_from=2026-10-01&jus_search=Luis");

    await waitFor(() =>
      expect(attendanceServiceMock.listJustifications).toHaveBeenCalledWith(
        expect.objectContaining({
          status: "pending",
          date_from: "2026-10-01",
          search: "Luis",
        })
      )
    );
  });

  test("rechazar exige comentario y resuelve con approved=false", async () => {
    attendanceServiceMock.resolveJustification.mockResolvedValue({
      ...JUSTIFICATION,
      status: "rejected",
    });
    const user = userEvent.setup();
    renderRequests();

    await user.click(
      await screen.findByRole("button", { name: "Acciones de Luis Perez" })
    );
    await user.click(await screen.findByRole("menuitem", { name: "Rechazar" }));
    const dialog = await screen.findByRole("dialog", {
      name: "Rechazar justificación",
    });
    await user.click(within(dialog).getByRole("button", { name: "Rechazar" }));
    expect(
      within(dialog).getByText(
        "Escriba el motivo del rechazo: queda registrado."
      )
    ).toBeInTheDocument();
    expect(attendanceServiceMock.resolveJustification).not.toHaveBeenCalled();

    await user.type(
      within(dialog).getByLabelText(/Motivo del rechazo/),
      "Sin respaldo"
    );
    await user.click(within(dialog).getByRole("button", { name: "Rechazar" }));

    await waitFor(() =>
      expect(attendanceServiceMock.resolveJustification).toHaveBeenCalledWith(
        "jus-1",
        { approved: false, comment: "Sin respaldo" }
      )
    );
    expect(
      await screen.findByText("Se rechazó la justificación de Luis Perez.")
    ).toBeInTheDocument();
  });

  test("el detalle permite aprobar sin comentario y ver el adjunto auditado", async () => {
    attendanceServiceMock.resolveJustification.mockResolvedValue({
      ...JUSTIFICATION,
      status: "approved",
    });
    attendanceServiceMock.getJustificationAttachment.mockResolvedValue({
      public_id: "att-1",
      filename: "constancia.pdf",
      content_type: "application/pdf",
      size_bytes: 20480,
      created_at: "2026-10-16T15:00:00Z",
    });
    const user = userEvent.setup();
    renderRequests();

    await user.click(await screen.findByText("Luis Perez"));
    const detail = await screen.findByRole("dialog", { name: "Justificación" });
    expect(screen.getByTestId("location")).toHaveTextContent("jus_id=jus-1");
    expect(await within(detail).findByText("Cita médica")).toBeInTheDocument();
    expect(
      within(detail).getByText(/queda registrado en la bitácora/)
    ).toBeInTheDocument();
    // El adjunto se consulta solo cuando la persona lo pide: queda auditado.
    expect(
      attendanceServiceMock.getJustificationAttachment
    ).not.toHaveBeenCalled();
    await user.click(
      within(detail).getByRole("button", { name: "Ver adjunto" })
    );
    expect(
      await within(detail).findByText("constancia.pdf")
    ).toBeInTheDocument();
    expect(within(detail).getByText("20 KB")).toBeInTheDocument();

    await user.click(within(detail).getByRole("button", { name: "Aprobar" }));
    const dialog = await screen.findByRole("dialog", {
      name: "Aprobar justificación",
    });
    await user.click(within(dialog).getByRole("button", { name: "Aprobar" }));
    await waitFor(() =>
      expect(attendanceServiceMock.resolveJustification).toHaveBeenCalledWith(
        "jus-1",
        { approved: true, comment: "" }
      )
    );
  });

  test("quien solo presenta no ve Aprobar ni Rechazar ni la excepción al plazo", async () => {
    const user = userEvent.setup();
    renderRequests("", sessionUser([REQUEST]));

    await user.click(
      await screen.findByRole("button", { name: "Acciones de Luis Perez" })
    );
    expect(
      await screen.findByRole("menuitem", { name: "Ver detalle" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("menuitem", { name: "Aprobar" })
    ).not.toBeInTheDocument();
    await user.keyboard("{Escape}");

    await user.click(
      screen.getByRole("button", { name: "Nueva justificación" })
    );
    const form = await screen.findByRole("dialog", {
      name: "Nueva justificación",
    });
    expect(
      within(form).queryByLabelText(/excepción al plazo/)
    ).not.toBeInTheDocument();
    // Una sola bandeja: no hay selector de bandeja.
    expect(
      screen.queryByRole("group", { name: "Bandeja" })
    ).not.toBeInTheDocument();
  });

  test("presenta una justificación y luego adjunta el respaldo una vez", async () => {
    const created = {
      ...JUSTIFICATION,
      public_id: "jus-2",
      has_attachment: false,
    };
    attendanceServiceMock.createJustification.mockResolvedValue(created);
    attendanceServiceMock.uploadJustificationAttachment.mockResolvedValue({});
    const user = userEvent.setup();
    renderRequests();

    await user.click(
      await screen.findByRole("button", { name: "Nueva justificación" })
    );
    const form = await screen.findByRole("dialog", {
      name: "Nueva justificación",
    });
    await pickStudent(user, within(form));
    await selectOption(user, /^Motivo del catálogo/, "Salud", form);
    await user.type(within(form).getByLabelText(/^Motivo$|^Motivo \*/), "Cita");
    await user.click(
      within(form).getByLabelText("Registrar como excepción al plazo")
    );
    await user.type(
      within(form).getByLabelText(/^Motivo de la excepción/),
      "Hospitalización"
    );
    await user.click(
      within(form).getByRole("button", { name: "Presentar justificación" })
    );

    await waitFor(() =>
      expect(attendanceServiceMock.createJustification).toHaveBeenCalledWith({
        student_id: "student-1",
        absence_date: todayInputValue(),
        situation_type: "absence",
        reason_catalog_id: "r-1",
        reason: "Cita",
        is_exception: true,
        exception_reason: "Hospitalización",
      })
    );

    const attach = await screen.findByRole("dialog", {
      name: "Adjuntar respaldo (opcional)",
    });
    const file = new File(["%PDF"], "constancia.pdf", {
      type: "application/pdf",
    });
    await user.upload(
      within(attach).getByLabelText("Documento de respaldo"),
      file
    );
    await user.click(within(attach).getByRole("button", { name: "Adjuntar" }));

    await waitFor(() =>
      expect(
        attendanceServiceMock.uploadJustificationAttachment
      ).toHaveBeenCalledWith("jus-2", file)
    );
    expect(
      await screen.findByText(
        "Justificación presentada; queda pendiente de resolver."
      )
    ).toBeInTheDocument();
  });
});

describe("Permisos de salida (AS4)", () => {
  test("cambia de bandeja con la URL y filtra por tipo", async () => {
    const user = userEvent.setup();
    renderRequests();
    await screen.findByText("Luis Perez");

    await user.click(
      screen.getByRole("button", { name: "Permisos de salida" })
    );

    expect(
      await screen.findByRole("heading", {
        name: "Permisos de salida e ingreso",
      })
    ).toBeInTheDocument();
    expect(screen.getByTestId("location")).toHaveTextContent(
      "bandeja=permisos"
    );
    const row = (await screen.findByText("Salida anticipada")).closest("tr");
    expect(within(row).getByText("11:30")).toBeInTheDocument();

    await selectOption(user, /^Tipo$|^Tipo/, "Ingreso tardío");
    await waitFor(() =>
      expect(attendanceServiceMock.listPermits).toHaveBeenLastCalledWith(
        expect.objectContaining({
          status: "pending",
          permit_type: "late_arrival",
        })
      )
    );
  });

  test("solicita un permiso con su hora prevista", async () => {
    attendanceServiceMock.createPermit.mockResolvedValue(PERMIT);
    const user = userEvent.setup();
    renderRequests("&bandeja=permisos");

    await user.click(
      await screen.findByRole("button", { name: "Nuevo permiso" })
    );
    const form = await screen.findByRole("dialog", { name: "Nuevo permiso" });
    await pickStudent(user, within(form));
    await user.type(within(form).getByLabelText(/^Hora prevista/), "11:30");
    await user.type(within(form).getByLabelText(/^Motivo/), "Consulta");
    await user.click(
      within(form).getByRole("button", { name: "Solicitar permiso" })
    );

    await waitFor(() =>
      expect(attendanceServiceMock.createPermit).toHaveBeenCalledWith({
        student_id: "student-1",
        permit_type: "early_exit",
        permit_date: todayInputValue(),
        scheduled_time: "11:30",
        reason: "Consulta",
      })
    );
  });

  test("aprueba un permiso desde su menú", async () => {
    attendanceServiceMock.resolvePermit.mockResolvedValue({
      ...PERMIT,
      status: "approved",
    });
    const user = userEvent.setup();
    renderRequests("&bandeja=permisos");

    await user.click(
      await screen.findByRole("button", { name: "Acciones de Luis Perez" })
    );
    await user.click(await screen.findByRole("menuitem", { name: "Aprobar" }));
    const dialog = await screen.findByRole("dialog", {
      name: "Aprobar permiso",
    });
    await user.type(within(dialog).getByLabelText(/Comentario/), "Autorizado");
    await user.click(within(dialog).getByRole("button", { name: "Aprobar" }));

    await waitFor(() =>
      expect(attendanceServiceMock.resolvePermit).toHaveBeenCalledWith(
        "per-1",
        { approved: true, comment: "Autorizado" }
      )
    );
    expect(
      await screen.findByText("Se aprobó el permiso de Luis Perez.")
    ).toBeInTheDocument();
  });
});
