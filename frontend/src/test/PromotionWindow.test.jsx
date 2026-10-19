import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { ThemeProvider } from "@mui/material/styles";
import { theme } from "@theme/theme.js";

import { PromotionWindow } from "@enrolments/PromotionWindow.jsx";
import { enrolmentsService } from "@enrolments/enrolmentsService.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

vi.mock("@enrolments/enrolmentsService.js", () => ({
  enrolmentsService: { getPromotion: vi.fn() },
}));

const RESULT = {
  enrolment_id: "enrolment-1",
  promoted: true,
  condition: "promoted",
  progression: "promoted",
  eligible_grade_id: "grade-2",
  eligible_grade_name: "Segundo básico",
  failed_subjects: [],
  total_subjects: 8,
  result_source: "live",
};
const CONTEXT = [{ label: "Estudiante", value: "Ana Demo · EST-001" }];

function windowFor(id = "enrolment-1", onClose = vi.fn()) {
  return (
    <PromotionWindow
      context={CONTEXT}
      enrolment={{ public_id: id }}
      onClose={onClose}
    />
  );
}

describe("consulta de promoción M4", () => {
  beforeEach(() => {
    enrolmentsService.getPromotion.mockReset().mockResolvedValue(RESULT);
  });

  it("consulta solo la matrícula elegida y muestra grado y fuente provisional", async () => {
    renderWithRouter(windowFor());
    expect(
      await screen.findByRole("heading", { name: "Promovido" })
    ).toBeInTheDocument();
    expect(screen.getByText("Segundo básico")).toBeInTheDocument();
    expect(screen.getByText("Ana Demo · EST-001")).toBeInTheDocument();
    expect(
      screen.getByText(/Resultado calculado con las notas actuales/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/no crea ni modifica matrículas/)
    ).toBeInTheDocument();
    expect(enrolmentsService.getPromotion).toHaveBeenCalledExactlyOnceWith(
      "enrolment-1"
    );
  });

  it("presenta repitencia y subáreas pendientes del resultado congelado", async () => {
    enrolmentsService.getPromotion.mockResolvedValue({
      ...RESULT,
      promoted: false,
      condition: "not_promoted",
      progression: "repeating",
      eligible_grade_name: "Primero básico",
      result_source: "frozen",
      failed_subjects: ["Matemática", "Comunicación"],
    });
    renderWithRouter(windowFor());
    expect(
      await screen.findByRole("heading", { name: /Repitencia/ })
    ).toBeInTheDocument();
    expect(screen.getByText("Primero básico")).toBeInTheDocument();
    expect(
      screen.getByText(/Resultado congelado al cierre/)
    ).toBeInTheDocument();
    const subjects = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(subjects.map((item) => item.textContent)).toEqual([
      "Matemática",
      "Comunicación",
    ]);
  });

  it("muestra graduación sin ofrecer una matrícula siguiente", async () => {
    enrolmentsService.getPromotion.mockResolvedValue({
      ...RESULT,
      progression: "graduated",
      eligible_grade_id: null,
      eligible_grade_name: null,
    });
    renderWithRouter(windowFor());
    expect(
      await screen.findByRole("heading", { name: "Graduación" })
    ).toBeInTheDocument();
    expect(
      screen.getByText("Sin grado siguiente por graduación")
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Reinscribir|Matricular/ })
    ).not.toBeInTheDocument();
  });

  it("advierte un resultado sin subáreas sin inventar otra decisión", async () => {
    enrolmentsService.getPromotion.mockResolvedValue({
      ...RESULT,
      total_subjects: 0,
    });
    renderWithRouter(windowFor());
    expect(
      await screen.findByText(/no reporta subáreas evaluadas/)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Promovido" })
    ).toBeInTheDocument();
  });

  it("presenta la denegación sin resultados y permite reintentar explícitamente", async () => {
    enrolmentsService.getPromotion.mockRejectedValueOnce(
      new Error("Sin alcance sobre la sección.")
    );
    const user = userEvent.setup();
    renderWithRouter(windowFor());
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Sin alcance sobre la sección."
    );
    expect(screen.queryByText("Segundo básico")).not.toBeInTheDocument();
    expect(enrolmentsService.getPromotion).toHaveBeenCalledTimes(1);
    await user.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Segundo básico")).toBeInTheDocument();
    expect(enrolmentsService.getPromotion).toHaveBeenCalledTimes(2);
  });

  it("ignora una respuesta tardía de otra matrícula", async () => {
    let resolveOld;
    enrolmentsService.getPromotion.mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveOld = resolve;
        })
    );
    const { rerender } = render(windowFor(), {
      wrapper: ({ children }) => (
        <ThemeProvider theme={theme}>{children}</ThemeProvider>
      ),
    });
    expect(screen.getByRole("status")).toHaveTextContent(
      "Consultando promoción"
    );
    rerender(windowFor("enrolment-2"));
    await screen.findByText("Segundo básico");
    await act(async () =>
      resolveOld({ ...RESULT, eligible_grade_name: "Resultado anterior" })
    );
    expect(screen.queryByText("Resultado anterior")).not.toBeInTheDocument();
    expect(enrolmentsService.getPromotion).toHaveBeenLastCalledWith(
      "enrolment-2"
    );
  });

  it("permite cerrar durante una consulta sin realizar escrituras", async () => {
    enrolmentsService.getPromotion.mockReturnValue(new Promise(() => {}));
    const close = vi.fn();
    const user = userEvent.setup();
    renderWithRouter(windowFor("enrolment-1", close));
    await user.click(screen.getAllByRole("button", { name: "Cerrar" })[1]);
    await waitFor(() => expect(close).toHaveBeenCalledOnce());
  });
});
