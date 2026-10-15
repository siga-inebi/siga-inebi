import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { EnrolmentDocumentsWindow } from "@enrolments/EnrolmentDocumentsWindow.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const documentsServiceMock = vi.hoisted(() => ({
  issuanceEligibility: vi.fn(),
  listEnrolmentRecords: vi.fn(),
  uploadRecord: vi.fn(),
  issueIndividualDocument: vi.fn(),
}));

vi.mock("@documents/documentsService.js", () => ({
  documentsService: documentsServiceMock,
}));

vi.mock("@enrolments/enrolmentsService.js", async (importOriginal) => {
  const original = await importOriginal();
  return {
    ...original,
    enrolmentsService: {
      listDocuments: vi.fn().mockResolvedValue({ count: 0, results: [] }),
      addDocument: vi.fn(),
    },
  };
});

const downloadBlobMock = vi.hoisted(() => vi.fn());

vi.mock("@shared/utils/download.js", async (importOriginal) => {
  const original = await importOriginal();
  return { ...original, downloadBlob: downloadBlobMock };
});

const ENROLMENT = { public_id: "enrolment-1", student_id: "student-1" };

function renderWindow() {
  return renderWithRouter(
    <EnrolmentDocumentsWindow enrolment={ENROLMENT} onClose={() => {}} />
  );
}

describe("EnrolmentDocumentsWindow emision individual (RF-EMI-001)", () => {
  beforeEach(() => {
    downloadBlobMock.mockReset();
    documentsServiceMock.issueIndividualDocument.mockReset();
    documentsServiceMock.issuanceEligibility.mockResolvedValue({
      eligible: true,
      blocking_document_codes: [],
    });
    documentsServiceMock.listEnrolmentRecords.mockResolvedValue({
      count: 0,
      results: [],
    });
  });

  test("emite la constancia, descarga el PDF y muestra folio y codigo", async () => {
    const blob = new Blob(["%PDF-1.4"], { type: "application/pdf" });
    documentsServiceMock.issueIndividualDocument.mockResolvedValue({
      blob,
      headers: new Headers({
        "Content-Disposition":
          'attachment; filename="enrolment_certificate-DEMO-2026-0001.pdf"',
        "X-Document-Folio": "DEMO-2026-0001",
        "X-Document-Verification-Code": "codigo-publico",
      }),
    });
    const user = userEvent.setup();
    renderWindow();

    await user.click(
      await screen.findByRole("button", { name: "Emitir constancia" })
    );

    await waitFor(() =>
      expect(documentsServiceMock.issueIndividualDocument).toHaveBeenCalledWith(
        "enrolment-1",
        "enrolment_certificate"
      )
    );
    expect(downloadBlobMock).toHaveBeenCalledWith(
      "enrolment_certificate-DEMO-2026-0001.pdf",
      blob
    );
    expect(
      await screen.findByText(/Folio DEMO-2026-0001; codigo de verificacion/)
    ).toBeInTheDocument();
  });

  test("muestra el motivo cuando el certificado se rechaza", async () => {
    documentsServiceMock.issueIndividualDocument.mockRejectedValue(
      new Error(
        "El certificado de estudios solo puede emitirse para un ciclo cerrado."
      )
    );
    const user = userEvent.setup();
    renderWindow();

    await user.click(
      await screen.findByRole("button", { name: "Emitir certificado" })
    );

    expect(
      await screen.findByText(
        "El certificado de estudios solo puede emitirse para un ciclo cerrado."
      )
    ).toBeInTheDocument();
    expect(documentsServiceMock.issueIndividualDocument).toHaveBeenCalledWith(
      "enrolment-1",
      "study_certificate"
    );
    expect(downloadBlobMock).not.toHaveBeenCalled();
  });
});
