import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { TeacherDocumentsWindow } from "@teachers/TeacherDocumentsWindow.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const documentsServiceMock = vi.hoisted(() => ({
  listTeacherRecords: vi.fn(),
  uploadTeacherRecord: vi.fn(),
  issueDownloadToken: vi.fn(),
}));

vi.mock("@documents/documentsService.js", () => ({
  documentsService: documentsServiceMock,
}));

const TEACHER = { id: 7, public_id: "teacher-uuid-7" };

const RECORD = {
  public_id: "record-1",
  teacher_id: "teacher-uuid-7",
  student_id: null,
  filename: "titulo.pdf",
  version_number: 2,
  status: "active",
  created_at: "2026-10-14T10:00:00Z",
};

function renderWindow() {
  return renderWithRouter(
    <TeacherDocumentsWindow
      onClose={() => {}}
      teacher={TEACHER}
      teacherName="Marta Xicara"
    />
  );
}

describe("TeacherDocumentsWindow (RF-DOC-001)", () => {
  beforeEach(() => {
    documentsServiceMock.listTeacherRecords.mockReset();
    documentsServiceMock.uploadTeacherRecord.mockReset();
    documentsServiceMock.issueDownloadToken.mockReset();
    documentsServiceMock.listTeacherRecords.mockResolvedValue({
      count: 1,
      results: [RECORD],
    });
  });

  test("lists the teacher's dossier by its public id", async () => {
    renderWindow();

    expect(await screen.findByText("titulo.pdf")).toBeInTheDocument();
    expect(screen.getByText("v2")).toBeInTheDocument();
    expect(documentsServiceMock.listTeacherRecords).toHaveBeenCalledWith(
      "teacher-uuid-7",
      expect.any(Object)
    );
  });

  test("downloads through a short-lived token", async () => {
    documentsServiceMock.issueDownloadToken.mockResolvedValue({
      token: "abc",
      download_url: "/api/v1/documents/records/record-1/download/?token=abc",
    });
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});
    const user = userEvent.setup();
    renderWindow();

    await user.click(
      await screen.findByRole("button", { name: "Descargar titulo.pdf" })
    );

    await waitFor(() =>
      expect(documentsServiceMock.issueDownloadToken).toHaveBeenCalledWith(
        "record-1"
      )
    );
    expect(click).toHaveBeenCalledTimes(1);
    click.mockRestore();
  });

  test("shows the API error when the token is refused", async () => {
    documentsServiceMock.issueDownloadToken.mockRejectedValue(
      new Error("El actor no tiene el alcance requerido.")
    );
    const user = userEvent.setup();
    renderWindow();

    await user.click(
      await screen.findByRole("button", { name: "Descargar titulo.pdf" })
    );

    expect(
      await screen.findByText("El actor no tiene el alcance requerido.")
    ).toBeInTheDocument();
  });

  test("uploads a file into the teacher's dossier", async () => {
    documentsServiceMock.uploadTeacherRecord.mockResolvedValue(RECORD);
    const user = userEvent.setup();
    renderWindow();
    await screen.findByText("titulo.pdf");

    await user.click(
      screen.getAllByRole("button", { name: "Adjuntar documento" })[0]
    );
    const file = new File(["%PDF-1.4"], "contrato.pdf", {
      type: "application/pdf",
    });
    await user.upload(screen.getByLabelText(/^Documento/), file);
    const submitButtons = screen.getAllByRole("button", {
      name: "Adjuntar documento",
    });
    await user.click(submitButtons[submitButtons.length - 1]);

    await waitFor(() =>
      expect(documentsServiceMock.uploadTeacherRecord).toHaveBeenCalledTimes(1)
    );
    const [teacherId, payload] =
      documentsServiceMock.uploadTeacherRecord.mock.calls[0];
    expect(teacherId).toBe("teacher-uuid-7");
    expect(payload.get("file").name).toBe("contrato.pdf");
  });
});
