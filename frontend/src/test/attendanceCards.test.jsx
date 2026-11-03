import { configure, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { afterEach, vi } from "vitest";

// Cada pestaña, bandeja y formulario se descarga diferido: bajo la carga de la
// suite completa el primer chunk puede tardar más que el segundo por omisión.
configure({ asyncUtilTimeout: 5000 });

const attendanceServiceMock = vi.hoisted(() => ({
  cardStatus: vi.fn(),
  issueCard: vi.fn(),
  cardPrintContent: vi.fn(),
  revokeCard: vi.fn(),
  revealCardQr: vi.fn(),
  exportCards: vi.fn(),
  listEvents: vi.fn(),
}));
const studentsServiceMock = vi.hoisted(() => ({
  listPage: vi.fn(),
  getRecord: vi.fn(),
  getRecordStatus: vi.fn(),
}));

const downloadMock = vi.hoisted(() => vi.fn());
vi.mock("@shared/utils/download.js", async (importOriginal) => ({
  ...(await importOriginal()),
  downloadResponseFile: downloadMock,
}));

vi.mock("@attendance/attendanceService.js", async () => {
  const actual = await vi.importActual("@attendance/attendanceService.js");
  return { ...actual, attendanceService: attendanceServiceMock };
});
vi.mock("@students/studentsService.js", async () => {
  const actual = await vi.importActual("@students/studentsService.js");
  return { ...actual, studentsService: studentsServiceMock };
});

import { AttendancePage } from "@attendance/AttendancePage.jsx";
import { StudentRecordPage } from "@students/StudentRecordPage.jsx";
import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";

const ISSUER = sessionUser(["attendance.credential.issue"]);
const PRINTER = sessionUser([
  "attendance.credential.issue",
  "attendance.credential.print",
]);
const paged = (results) => ({ count: results.length, results });
const STUDENT = {
  public_id: "student-1",
  student_code: "EST-1",
  person: { first_name: "Luis", last_name: "Perez" },
};
const NONE = {
  student_id: "student-1",
  status: "none",
  public_id: null,
  issued_at: null,
  revoked_at: null,
  revocation_reason: null,
};
const ACTIVE = {
  ...NONE,
  status: "active",
  public_id: "card-1",
  issued_at: "2026-10-19T14:00:00Z",
};
const ISSUED = {
  public_id: "card-1",
  student_id: "student-1",
  opaque_identifier: "opaque-token",
  qr_code: "iVBORw0KGgo=",
  status: "active",
  issued_at: "2026-10-19T14:00:00Z",
};
beforeEach(() => {
  Object.values(attendanceServiceMock).forEach((mock) => mock.mockReset());
  studentsServiceMock.listPage.mockReset().mockResolvedValue(paged([STUDENT]));
  attendanceServiceMock.cardStatus.mockResolvedValue(NONE);
  downloadMock.mockReset();
});
afterEach(() => vi.restoreAllMocks());

function renderCards(query = "", user = ISSUER) {
  return renderWithSession(<AttendancePage />, {
    user,
    route: `/app/asistencia?tab=carnes${query}`,
  });
}

describe("Carnés (AS2)", () => {
  test("pide elegir un estudiante buscado en el servidor", async () => {
    const user = userEvent.setup();
    renderCards();

    expect(
      await screen.findByText(
        "Elija un estudiante para consultar o emitir su carné."
      )
    ).toBeInTheDocument();
    await user.type(screen.getByRole("combobox", { name: /Estudiante/ }), "Lu");
    await user.click(
      await screen.findByRole("option", { name: "Luis Perez · EST-1" })
    );

    expect(studentsServiceMock.listPage).toHaveBeenCalledWith({ search: "Lu" });
    await waitFor(() =>
      expect(attendanceServiceMock.cardStatus).toHaveBeenCalledWith("student-1")
    );
    expect(await screen.findByText("Sin carné")).toBeInTheDocument();
  });

  test("emite el carné, muestra el QR y lo descarga en PNG o PDF", async () => {
    attendanceServiceMock.issueCard.mockResolvedValue(ISSUED);
    const file = { blob: new Blob(["png"]), headers: new Headers() };
    attendanceServiceMock.exportCards.mockResolvedValue(file);
    const user = userEvent.setup();
    renderCards("&estudiante=student-1", PRINTER);

    await user.click(
      await screen.findByRole("button", { name: "Emitir carné" })
    );

    expect(attendanceServiceMock.issueCard).toHaveBeenCalledWith("student-1");
    const qr = await screen.findByRole("img", { name: /Código QR del carné/ });
    expect(qr).toHaveAttribute("src", "data:image/png;base64,iVBORw0KGgo=");
    expect(screen.queryByText(/Imprímalo ahora/)).not.toBeInTheDocument();
    // El QR de la emisión ya está en memoria: no se vuelve a pedir.
    expect(attendanceServiceMock.revealCardQr).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Descargar PNG" }));
    await waitFor(() =>
      expect(downloadMock).toHaveBeenCalledWith(file, "carne-student-1.png")
    );
    expect(attendanceServiceMock.exportCards).toHaveBeenCalledWith(
      ["student-1"],
      "png"
    );
    await user.click(screen.getByRole("button", { name: "Descargar PDF" }));
    await waitFor(() =>
      expect(attendanceServiceMock.exportCards).toHaveBeenLastCalledWith(
        ["student-1"],
        "pdf"
      )
    );
  });

  test("con permiso de impresión el carné vigente vuelve a mostrar su QR", async () => {
    attendanceServiceMock.cardStatus.mockResolvedValue(ACTIVE);
    attendanceServiceMock.revealCardQr.mockResolvedValue({
      qr_code: "QRVIGENTE=",
    });
    renderCards("&estudiante=student-1", PRINTER);

    const qr = await screen.findByRole("img", { name: /Código QR del carné/ });
    expect(qr).toHaveAttribute("src", "data:image/png;base64,QRVIGENTE=");
    expect(attendanceServiceMock.revealCardQr).toHaveBeenCalledWith(
      "student-1"
    );
    expect(
      screen.getByRole("button", { name: "Descargar PNG" })
    ).toBeInTheDocument();
  });

  test("sin permiso de impresión no pide el QR ni ofrece descargas", async () => {
    attendanceServiceMock.cardStatus.mockResolvedValue(ACTIVE);
    renderCards("&estudiante=student-1");

    expect(await screen.findByText("Vigente")).toBeInTheDocument();
    expect(
      screen.getByText(/se necesita el permiso de impresión/)
    ).toBeInTheDocument();
    expect(attendanceServiceMock.revealCardQr).not.toHaveBeenCalled();
    expect(
      screen.queryByRole("button", { name: /Descargar/ })
    ).not.toBeInTheDocument();
  });

  test("avisa si la descarga del carné falla", async () => {
    attendanceServiceMock.cardStatus.mockResolvedValue(ACTIVE);
    attendanceServiceMock.revealCardQr.mockResolvedValue({ qr_code: "QR=" });
    attendanceServiceMock.exportCards.mockRejectedValue(
      new Error("El estudiante no tiene matrícula activa.")
    );
    const user = userEvent.setup();
    renderCards("&estudiante=student-1", PRINTER);

    await user.click(
      await screen.findByRole("button", { name: "Descargar PDF" })
    );
    expect(
      await screen.findByText("El estudiante no tiene matrícula activa.")
    ).toBeInTheDocument();
    expect(downloadMock).not.toHaveBeenCalled();
  });

  test("revocar exige motivo", async () => {
    attendanceServiceMock.cardStatus.mockResolvedValue(ACTIVE);
    attendanceServiceMock.revokeCard.mockResolvedValue({});
    const user = userEvent.setup();
    renderCards("&estudiante=student-1");

    expect(await screen.findByText("Vigente")).toBeInTheDocument();
    // Un carné vigente no se vuelve a emitir: primero se revoca.
    expect(
      screen.queryByRole("button", { name: /Emitir carné/ })
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Revocar carné" }));
    const dialog = await screen.findByRole("dialog", { name: "Revocar carné" });
    await user.click(
      within(dialog).getByRole("button", { name: "Revocar carné" })
    );
    expect(attendanceServiceMock.revokeCard).not.toHaveBeenCalled();

    await user.type(within(dialog).getByLabelText(/^Motivo/), "Extravío");
    await user.click(
      within(dialog).getByRole("button", { name: "Revocar carné" })
    );
    await waitFor(() =>
      expect(attendanceServiceMock.revokeCard).toHaveBeenCalledWith(
        "student-1",
        "Extravío"
      )
    );
  });

  test("un carné revocado muestra el motivo y ofrece emitir uno nuevo", async () => {
    attendanceServiceMock.cardStatus.mockResolvedValue({
      ...ACTIVE,
      status: "revoked",
      revoked_at: "2026-10-19T15:00:00Z",
      revocation_reason: "Extravío",
    });
    renderCards("&estudiante=student-1");

    expect(await screen.findByText("Revocado")).toBeInTheDocument();
    expect(screen.getByText(/Extravío/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Emitir carné nuevo" })
    ).toBeInTheDocument();
  });
});

describe("Carné en el expediente del estudiante", () => {
  test("la pestaña Carné aparece solo con attendance.credential.issue", async () => {
    studentsServiceMock.getRecord.mockResolvedValue({
      ...STUDENT,
      status: "active",
      photo: "",
      person: { ...STUDENT.person, public_id: "person-1" },
    });
    studentsServiceMock.getRecordStatus.mockResolvedValue({
      status: "active",
      can_change: false,
      last_change: null,
      warnings: [],
      options: [],
    });
    const user = userEvent.setup();
    const page = (
      <Routes>
        <Route path="/app/alumnos/:studentId" element={<StudentRecordPage />} />
      </Routes>
    );
    const { unmount } = renderWithSession(page, {
      user: sessionUser([]),
      route: "/app/alumnos/student-1",
    });
    await screen.findByRole("heading", { name: "Luis Perez" });
    expect(
      screen.queryByRole("tab", { name: "Carné" })
    ).not.toBeInTheDocument();
    unmount();

    renderWithSession(page, { user: ISSUER, route: "/app/alumnos/student-1" });
    await user.click(await screen.findByRole("tab", { name: "Carné" }));
    expect(
      await screen.findByRole("button", { name: "Emitir carné" })
    ).toBeInTheDocument();
    expect(attendanceServiceMock.cardStatus).toHaveBeenCalledWith("student-1");
  });
});
