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
  listEvents: vi.fn(),
}));
const studentsServiceMock = vi.hoisted(() => ({
  listPage: vi.fn(),
  getRecord: vi.fn(),
  getRecordStatus: vi.fn(),
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
const PRINT_CONTENT = {
  student_id: "student-1",
  full_name: "Luis Perez",
  grade_name: "Primero Básico",
  section_name: "A",
  academic_cycle_name: "Ciclo 2026",
  institution_name: "INEBI",
  photo_url: null,
};

beforeEach(() => {
  Object.values(attendanceServiceMock).forEach((mock) => mock.mockReset());
  studentsServiceMock.listPage.mockReset().mockResolvedValue(paged([STUDENT]));
  attendanceServiceMock.cardStatus.mockResolvedValue(NONE);
});
afterEach(() => vi.restoreAllMocks());

function renderCards(query = "") {
  return renderWithSession(<AttendancePage />, {
    user: ISSUER,
    route: `/app/asistencia?tab=carnes${query}`,
  });
}

function fakePrintWindow() {
  const written = [];
  const printWindow = {
    document: {
      write: (html) => written.push(html),
      close: vi.fn(),
      querySelector: () => ({ complete: true }),
    },
    focus: vi.fn(),
    print: vi.fn(),
  };
  vi.spyOn(window, "open").mockReturnValue(printWindow);
  return { printWindow, written };
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

  test("emite el carné, muestra el QR una vez e imprime con el contenido imprimible", async () => {
    attendanceServiceMock.issueCard.mockResolvedValue(ISSUED);
    attendanceServiceMock.cardPrintContent.mockResolvedValue(PRINT_CONTENT);
    const { printWindow, written } = fakePrintWindow();
    const user = userEvent.setup();
    renderCards("&estudiante=student-1");

    expect(
      await screen.findByText(/El código QR solo se muestra al emitir/)
    ).toBeInTheDocument();
    await user.click(
      await screen.findByRole("button", { name: "Emitir carné" })
    );

    expect(attendanceServiceMock.issueCard).toHaveBeenCalledWith("student-1");
    const qr = await screen.findByRole("img", { name: /Código QR del carné/ });
    expect(qr).toHaveAttribute("src", "data:image/png;base64,iVBORw0KGgo=");

    await user.click(screen.getByRole("button", { name: "Imprimir carné" }));
    await waitFor(() => expect(printWindow.print).toHaveBeenCalled());
    expect(attendanceServiceMock.cardPrintContent).toHaveBeenCalledWith(
      "student-1"
    );
    const html = written.join("");
    expect(html).toContain("Luis Perez");
    expect(html).toContain("INEBI");
    expect(html).toContain("Primero Básico A");
    expect(html).toContain("data:image/png;base64,iVBORw0KGgo=");
  });

  test("avisa si el navegador bloquea la ventana de impresión", async () => {
    attendanceServiceMock.issueCard.mockResolvedValue(ISSUED);
    attendanceServiceMock.cardPrintContent.mockResolvedValue(PRINT_CONTENT);
    vi.spyOn(window, "open").mockReturnValue(null);
    const user = userEvent.setup();
    renderCards("&estudiante=student-1");

    await user.click(
      await screen.findByRole("button", { name: "Emitir carné" })
    );
    await user.click(
      await screen.findByRole("button", { name: "Imprimir carné" })
    );

    expect(
      await screen.findByText(/El navegador bloqueó la ventana de impresión/)
    ).toBeInTheDocument();
  });

  test("revocar exige motivo y explica cómo reimprimir", async () => {
    attendanceServiceMock.cardStatus.mockResolvedValue(ACTIVE);
    attendanceServiceMock.revokeCard.mockResolvedValue({});
    const user = userEvent.setup();
    renderCards("&estudiante=student-1");

    expect(await screen.findByText("Vigente")).toBeInTheDocument();
    // Un carné vigente no se vuelve a emitir: el QR no se puede repetir.
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
