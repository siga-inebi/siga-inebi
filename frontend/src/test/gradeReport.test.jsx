import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

const evaluationServiceMock = vi.hoisted(() => ({ getGradeReport: vi.fn() }));
const cyclesServiceMock = vi.hoisted(() => ({ list: vi.fn() }));
const studentsServiceMock = vi.hoisted(() => ({ listPage: vi.fn() }));
const pdfMock = vi.hoisted(() => ({
  buildGradeReportPdf: vi.fn(),
  gradeReportFilename: vi.fn(() => "informe.pdf"),
}));
const downloadMock = vi.hoisted(() => ({ downloadBlob: vi.fn() }));

vi.mock("@evaluation/evaluationService.js", async (importOriginal) => {
  const original = await importOriginal();
  return { ...original, evaluationService: evaluationServiceMock };
});
vi.mock("@cycles/cyclesService.js", async (importOriginal) => {
  const original = await importOriginal();
  return { ...original, cyclesService: cyclesServiceMock };
});
vi.mock("@students/studentsService.js", () => ({
  studentsService: studentsServiceMock,
}));
vi.mock("@academics/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});
vi.mock("@shared/catalogs/academicCatalogs.js", async (importOriginal) => {
  const original = await importOriginal();
  return {
    ...original,
    useGradeCatalog: () => ({
      options: [
        { value: "g-1", label: "Primero Básico" },
        { value: "g-2", label: "Segundo Básico" },
      ],
      loading: false,
      error: "",
    }),
  };
});
vi.mock("@evaluation/gradeReportPdf.js", () => pdfMock);
vi.mock("@shared/utils/download.js", async (importOriginal) => {
  const original = await importOriginal();
  return { ...original, downloadBlob: downloadMock.downloadBlob };
});

import { GradeReportPage } from "@evaluation/GradeReportPage.jsx";
import { paginated } from "./fixtures/academics.js";
import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";
import {
  academicsServiceMock,
  resetAcademicsServiceMock,
} from "./mocks/academicsService.js";
import { selectOption } from "./helpers/selectOption.jsx";

const PRINTER = sessionUser(["grade.report"]);
const CYCLE = {
  public_id: "c-2026",
  name: "Ciclo 2026",
  status: "active",
  year: 2026,
};

function reportWith(students) {
  return {
    institution: { name: "Instituto Demo", short_name: "DEMO" },
    cycle: { public_id: "c-2026", name: "Ciclo 2026", year: 2026 },
    generated_at: "2026-10-24T10:00:00-06:00",
    units: [
      { public_id: "u-1", number: 1, name: "Unidad 1" },
      { public_id: "u-2", number: 2, name: "Unidad 2" },
    ],
    students,
  };
}

const STUDENT = {
  student_code: "EST-1",
  student_name: "Ana López",
  grade_name: "Primero Básico",
  section_label: "Primero Básico A · Matutina",
  subjects: [
    { name: "Matemática", grades: [60, 61], average: 61 },
    { name: "Idioma Español", grades: [90, null], average: 90 },
  ],
  unit_averages: [75, 61],
  general_average: 70,
};

function renderPage() {
  return renderWithSession(<GradeReportPage />, {
    user: PRINTER,
    route: "/app/informe-de-notas",
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  resetAcademicsServiceMock();
  cyclesServiceMock.list.mockResolvedValue(paginated([CYCLE]));
  evaluationServiceMock.getGradeReport.mockResolvedValue(reportWith([STUDENT]));
  pdfMock.buildGradeReportPdf.mockResolvedValue(new Blob(["%PDF"]));
  academicsServiceMock.listSections.mockResolvedValue(
    paginated([
      { public_id: "sec-a", name: "A", shift: { name: "Matutina" } },
      { public_id: "sec-b", name: "B", shift: { name: "Matutina" } },
    ])
  );
});

describe("Informe de notas", () => {
  test("todos los estudiantes: pide el ciclo completo y descarga el PDF", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(
      await screen.findByRole("button", { name: "Generar PDF" })
    );

    await waitFor(() =>
      expect(downloadMock.downloadBlob).toHaveBeenCalledWith(
        "informe.pdf",
        expect.any(Blob)
      )
    );
    expect(evaluationServiceMock.getGradeReport).toHaveBeenCalledWith(
      "c-2026",
      {}
    );
    expect(pdfMock.buildGradeReportPdf).toHaveBeenCalledWith(
      reportWith([STUDENT]),
      expect.objectContaining({ onProgress: expect.any(Function) })
    );
    expect(
      screen.getByText("Se generó el informe de 1 estudiante.")
    ).toBeInTheDocument();
  });

  test("por grado exige el grado y acepta una sección opcional", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(
      await screen.findByRole("button", { name: "Un grado o sección" })
    );
    expect(screen.getByRole("button", { name: "Generar PDF" })).toBeDisabled();

    await selectOption(user, /Grado/, "Primero Básico");
    await selectOption(user, /Sección/, "Sección B · Matutina");
    await user.click(screen.getByRole("button", { name: "Generar PDF" }));

    await waitFor(() =>
      expect(evaluationServiceMock.getGradeReport).toHaveBeenCalledWith(
        "c-2026",
        { grade_id: "g-1", section_id: "sec-b" }
      )
    );
    expect(academicsServiceMock.listSections).toHaveBeenCalledWith(
      expect.objectContaining({ academic_cycle_id: "c-2026", grade_id: "g-1" })
    );
  });

  test("por estudiante busca en el servidor mientras se escribe", async () => {
    studentsServiceMock.listPage.mockResolvedValue(
      paginated([
        {
          public_id: "st-1",
          student_code: "EST-1",
          person: { first_name: "Ana", last_name: "López" },
        },
      ])
    );
    const user = userEvent.setup();
    renderPage();

    await user.click(
      await screen.findByRole("button", { name: "Un estudiante" })
    );
    await user.type(
      screen.getByRole("combobox", { name: "Estudiante" }),
      "Ana"
    );
    await user.click(await screen.findByRole("option", { name: /Ana López/ }));
    await user.click(screen.getByRole("button", { name: "Generar PDF" }));

    await waitFor(() =>
      expect(evaluationServiceMock.getGradeReport).toHaveBeenCalledWith(
        "c-2026",
        { student_id: "st-1" }
      )
    );
    expect(studentsServiceMock.listPage).toHaveBeenCalledWith(
      expect.objectContaining({ search: "Ana" })
    );
  });

  test("una selección sin estudiantes lo avisa y no arma PDF", async () => {
    evaluationServiceMock.getGradeReport.mockResolvedValue(reportWith([]));
    const user = userEvent.setup();
    renderPage();

    await user.click(
      await screen.findByRole("button", { name: "Generar PDF" })
    );

    expect(
      await screen.findByText(/No hay estudiantes con matrícula activa/)
    ).toBeInTheDocument();
    expect(pdfMock.buildGradeReportPdf).not.toHaveBeenCalled();
  });

  test("un rechazo del servidor se muestra", async () => {
    evaluationServiceMock.getGradeReport.mockRejectedValue(
      new Error("Permiso denegado: se requiere el permiso para imprimir notas.")
    );
    const user = userEvent.setup();
    renderPage();

    await user.click(
      await screen.findByRole("button", { name: "Generar PDF" })
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "se requiere el permiso para imprimir notas"
    );
  });
});

/** Bytes del PDF como texto latin-1 (generado con `compress: false`). */
async function pdfText(blob) {
  const buffer = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error);
    reader.readAsArrayBuffer(blob);
  });
  return Array.from(new Uint8Array(buffer), (byte) =>
    String.fromCharCode(byte)
  ).join("");
}

describe("PDF del informe", () => {
  const realBuild = async (...args) => {
    const actual = await vi.importActual("@evaluation/gradeReportPdf.js");
    return actual.buildGradeReportPdf(...args);
  };

  test("una página por estudiante, referencias cruzadas válidas y promedios", async () => {
    const second = {
      ...STUDENT,
      student_code: "EST-2",
      student_name: "Bruno Díaz",
      general_average: null,
    };
    const progress = vi.fn();

    const blob = await realBuild(reportWith([STUDENT, second]), {
      onProgress: progress,
      logo: null,
      compress: false,
    });
    const text = await pdfText(blob);

    expect(blob.type).toBe("application/pdf");
    expect(text.startsWith("%PDF-1.4")).toBe(true);
    expect(text).toContain("/Type /Pages");
    expect(text).toContain("/Count 2");
    // Cada entrada de la tabla xref apunta al inicio de su objeto.
    const start = Number(/startxref\n(\d+)/.exec(text)[1]);
    const xref = text.slice(start).split("\n");
    const count = Number(xref[1].split(" ")[1]);
    for (let number = 1; number < count; number += 1) {
      const offset = Number(xref[2 + number].slice(0, 10));
      expect(text.startsWith(`${number} 0 obj`, offset)).toBe(true);
    }
    // Texto con tildes en WinAnsi (octal), promedios y esquina general.
    expect(text).toContain("(Matem\\341tica) Tj");
    expect(text).toContain("(Ana L\\363pez) Tj");
    expect(text).toContain("(Promedio de la unidad) Tj");
    expect(text).toContain("(61) Tj");
    expect(text).toContain("(70) Tj");
    expect(text).toContain("(P\\341gina 2 de 2) Tj");
    // Sin nota se dibuja una raya (WinAnsi 0x97), nunca un cero.
    expect(text).toContain("(\\227) Tj");
    expect(progress).toHaveBeenLastCalledWith(2, 2);
  });

  test("comprimido sigue teniendo referencias cruzadas válidas y es más chico", async () => {
    const report = reportWith(Array.from({ length: 30 }, () => STUDENT));
    const plain = await realBuild(report, { logo: null, compress: false });
    const packed = await realBuild(report, { logo: null });
    const text = await pdfText(packed);

    const start = Number(/startxref\n(\d+)/.exec(text)[1]);
    const xref = text.slice(start).split("\n");
    const count = Number(xref[1].split(" ")[1]);
    for (let number = 1; number < count; number += 1) {
      const offset = Number(xref[2 + number].slice(0, 10));
      expect(text.startsWith(`${number} 0 obj`, offset)).toBe(true);
    }
    expect(text).toContain("/Count 30");
    if (typeof CompressionStream !== "undefined") {
      expect(text).toContain("/FlateDecode");
      expect(packed.size).toBeLessThan(plain.size / 2);
    }
  });

  test("escapa paréntesis y barras del texto", async () => {
    const tricky = {
      ...STUDENT,
      subjects: [
        { name: "Física (laboratorio) \\ A", grades: [80, 90], average: 85 },
      ],
    };

    const text = await pdfText(
      await realBuild(reportWith([tricky]), { logo: null, compress: false })
    );

    expect(text).toContain("(F\\355sica \\(laboratorio\\) \\\\ A) Tj");
  });
});
