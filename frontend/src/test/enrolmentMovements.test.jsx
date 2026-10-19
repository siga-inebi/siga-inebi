import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

const service = vi.hoisted(() => ({
  listMovements: vi.fn(),
  changeSection: vi.fn(),
  withdraw: vi.fn(),
  annulMovement: vi.fn(),
}));
const academics = vi.hoisted(() => ({ listSections: vi.fn() }));
vi.mock("@enrolments/enrolmentsService.js", async () => ({
  ...(await vi.importActual("@enrolments/enrolmentsService.js")),
  enrolmentsService: service,
}));
vi.mock("@academics/academicsService.js", async () => ({
  ...(await vi.importActual("@academics/academicsService.js")),
  academicsService: academics,
}));

import { MovementHistoryWindow } from "@enrolments/MovementHistoryWindow.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const source = {
  public_id: "enrolment-1",
  student_id: "student-1",
  academic_cycle_id: "cycle-1",
  grade_id: "grade-1",
  section_id: "section-1",
};
const withdrawal = {
  public_id: "movement-1",
  movement_type: "withdrawal",
  effective_on: "2026-03-01",
  created_at: "2026-03-02T10:00:00Z",
  reason: "Traslado familiar",
  annulment: null,
  supports_annulment: true,
};
const paged = (results, count = results.length) => ({
  count,
  results,
  next: null,
});

beforeEach(() => {
  service.listMovements.mockReset().mockResolvedValue(paged([]));
  service.changeSection
    .mockReset()
    .mockResolvedValue({ ...source, public_id: "replacement" });
  service.withdraw.mockReset().mockResolvedValue(withdrawal);
  service.annulMovement.mockReset().mockResolvedValue({
    public_id: "annulment-1",
    reason: "Corrección",
    created_at: "2026-03-03T10:00:00Z",
  });
  academics.listSections.mockReset().mockResolvedValue(
    paged([
      {
        public_id: "section-1",
        name: "A",
        grade: { name: "Primero" },
        shift: { name: "Matutina" },
      },
      {
        public_id: "section-2",
        name: "B",
        grade: { name: "Primero" },
        shift: { name: "Matutina" },
      },
    ])
  );
});

function mount(props = {}) {
  const onChanged = vi.fn();
  const onClose = vi.fn();
  renderWithRouter(
    <MovementHistoryWindow
      enrolment={source}
      studentId="student-1"
      studentLabel="Ana Demo · EST-1"
      enrolmentLabel="2026 · Primero · A"
      onChanged={onChanged}
      onClose={onClose}
      {...props}
    />
  );
  return { user: userEvent.setup(), onChanged, onClose };
}

async function choose(user, name, option) {
  await user.click(screen.getByRole("combobox", { name }));
  await user.click(await screen.findByRole("option", { name: option }));
}

async function startWithdrawal() {
  const state = mount();
  await state.user.click(
    screen.getByRole("tab", { name: "Registrar movimiento" })
  );
  await choose(state.user, "Tipo de movimiento", "Retiro");
  await state.user.type(screen.getByLabelText("Vigente desde"), "2026-03-01");
  await state.user.type(
    screen.getByLabelText(/Causa del retiro/),
    "Cambio familiar"
  );
  return state;
}

test("cambia sección usando contexto y filtros remotos, con revisión en una sola ventana", async () => {
  const { user, onChanged } = mount();
  expect(academics.listSections).not.toHaveBeenCalled();
  await user.click(screen.getByRole("tab", { name: "Registrar movimiento" }));
  await choose(user, "Sección de destino", "Primero · B · Matutina");
  expect(academics.listSections).toHaveBeenCalledWith(
    expect.objectContaining({
      academic_cycle_id: "cycle-1",
      grade_id: "grade-1",
    })
  );
  await user.type(screen.getByLabelText("Vigente desde"), "2026-03-01");
  await user.click(screen.getByRole("button", { name: "Revisar movimiento" }));
  expect(service.changeSection).not.toHaveBeenCalled();
  expect(screen.getAllByRole("dialog")).toHaveLength(1);
  await user.click(
    screen.getByRole("button", { name: "Confirmar cambio de sección" })
  );
  await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
  expect(service.changeSection).toHaveBeenCalledWith("enrolment-1", {
    new_section_id: "section-2",
    effective_on: "2026-03-01",
  });
  expect(
    screen.getByRole("tab", { name: "Registrar movimiento" })
  ).toBeDisabled();
  expect(service.listMovements).toHaveBeenLastCalledWith(
    expect.objectContaining({ student_id: "student-1" })
  );
});

test("retiro muestra consecuencias, exige causa y fecha y confirma solo tras revisar", async () => {
  const { user, onChanged } = await startWithdrawal();
  expect(screen.getByText(/El retiro cierra la matrícula/)).toBeInTheDocument();
  await user.clear(screen.getByLabelText(/Causa del retiro/));
  await user.click(screen.getByRole("button", { name: "Revisar movimiento" }));
  expect(await screen.findByText("Escriba el motivo.")).toBeInTheDocument();
  expect(service.withdraw).not.toHaveBeenCalled();
  await user.type(screen.getByLabelText(/Causa del retiro/), "Cambio familiar");
  await user.click(screen.getByRole("button", { name: "Revisar movimiento" }));
  expect(service.withdraw).not.toHaveBeenCalled();
  service.listMovements.mockResolvedValue(paged([withdrawal]));
  await user.click(screen.getByRole("button", { name: "Confirmar retiro" }));
  await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
  expect(service.withdraw).toHaveBeenCalledWith("enrolment-1", {
    reason: "Cambio familiar",
    effective_on: "2026-03-01",
  });
  expect(await screen.findByText("Traslado familiar")).toBeInTheDocument();
});

test("editar fecha después de revisar invalida la confirmación", async () => {
  const { user } = await startWithdrawal();
  await user.click(screen.getByRole("button", { name: "Revisar movimiento" }));
  expect(
    screen.getByRole("button", { name: "Confirmar retiro" })
  ).toBeInTheDocument();
  await user.clear(screen.getByLabelText("Vigente desde"));
  expect(
    screen.queryByRole("button", { name: "Confirmar retiro" })
  ).not.toBeInTheDocument();
  expect(service.withdraw).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Revisar movimiento" }));
  expect(
    await screen.findByText("Indique la fecha de vigencia.")
  ).toBeInTheDocument();
});

test("rechazo por permisos o estado conserva borrador y permite consultar historial actualizado", async () => {
  const { user, onChanged } = await startWithdrawal();
  service.withdraw.mockRejectedValueOnce(
    new Error("El actor no tiene alcance sobre la seccion afectada.")
  );
  await user.click(screen.getByRole("button", { name: "Revisar movimiento" }));
  await user.click(screen.getByRole("button", { name: "Confirmar retiro" }));
  expect(
    await screen.findByText(/El actor no tiene alcance/)
  ).toBeInTheDocument();
  expect(screen.getByLabelText(/Causa del retiro/)).toHaveValue(
    "Cambio familiar"
  );
  expect(screen.getByLabelText("Vigente desde")).toHaveValue("2026-03-01");
  expect(
    screen.queryByRole("button", { name: "Confirmar retiro" })
  ).not.toBeInTheDocument();
  expect(service.withdraw).toHaveBeenCalledTimes(1);
  expect(onChanged).toHaveBeenCalledTimes(1);
  await user.click(screen.getByRole("button", { name: "Volver al historial" }));
  expect(screen.getByRole("tab", { name: "Historial" })).toHaveAttribute(
    "aria-selected",
    "true"
  );
});

test("anula por UUID del movimiento y conserva evidencia visible del original", async () => {
  service.listMovements.mockResolvedValue(paged([withdrawal]));
  const { user, onChanged } = mount({ enrolment: undefined });
  expect(
    screen.getByRole("tab", { name: "Registrar movimiento" })
  ).toBeDisabled();
  await user.click(
    await screen.findByRole("button", { name: "Anular movimiento" })
  );
  await user.type(
    screen.getByLabelText(/Motivo de anulación/),
    "Estudiante equivocado"
  );
  await user.click(screen.getByRole("button", { name: "Revisar movimiento" }));
  service.listMovements.mockResolvedValue(
    paged([
      {
        ...withdrawal,
        annulment: {
          reason: "Estudiante equivocado",
          created_at: "2026-03-03T10:00:00Z",
        },
      },
    ])
  );
  expect(service.annulMovement).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Confirmar anulación" }));
  expect(await screen.findByText("Anulado")).toBeInTheDocument();
  expect(screen.getByText("Estudiante equivocado")).toBeInTheDocument();
  expect(screen.getByText("Traslado familiar")).toBeInTheDocument();
  expect(service.annulMovement).toHaveBeenCalledWith("movement-1", {
    reason: "Estudiante equivocado",
  });
  expect(onChanged).toHaveBeenCalledTimes(1);
  expect(
    screen.queryByRole("button", { name: "Anular movimiento" })
  ).not.toBeInTheDocument();
});

test("tipo no reversible no ofrece anulación aunque no esté anulado", async () => {
  service.listMovements.mockResolvedValue(
    paged([
      {
        ...withdrawal,
        movement_type: "transfer_out",
        supports_annulment: false,
      },
    ])
  );
  mount();
  await screen.findByText("Traslado de egreso");
  expect(
    screen.queryByRole("button", { name: "Anular movimiento" })
  ).not.toBeInTheDocument();
});

test("pagina historial y anula únicamente el movimiento de la página consultada", async () => {
  service.listMovements.mockImplementation(({ page }) =>
    Promise.resolve(
      paged(
        [
          {
            ...withdrawal,
            public_id: page === 2 ? "movement-page-2" : "movement-1",
          },
        ],
        26
      )
    )
  );
  const { user } = mount();
  await screen.findByText("Traslado familiar");
  await user.click(screen.getByRole("button", { name: "Siguiente" }));
  await waitFor(() =>
    expect(service.listMovements).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 2, student_id: "student-1" })
    )
  );
  await user.click(
    await screen.findByRole("button", { name: "Anular movimiento" })
  );
  await user.type(
    screen.getByLabelText(/Motivo de anulación/),
    "Corregir segunda página"
  );
  await user.click(screen.getByRole("button", { name: "Revisar movimiento" }));
  await user.click(screen.getByRole("button", { name: "Confirmar anulación" }));
  await waitFor(() =>
    expect(service.annulMovement).toHaveBeenCalledWith("movement-page-2", {
      reason: "Corregir segunda página",
    })
  );
});

test("bloquea cierre y doble confirmación durante una escritura", async () => {
  const { user, onClose } = await startWithdrawal();
  let resolveWrite;
  service.withdraw.mockReturnValueOnce(
    new Promise((resolve) => {
      resolveWrite = resolve;
    })
  );
  await user.click(screen.getByRole("button", { name: "Revisar movimiento" }));
  await user.click(screen.getByRole("button", { name: "Confirmar retiro" }));
  expect(screen.getByRole("button", { name: "Procesando…" })).toBeDisabled();
  await user.click(screen.getByLabelText("Cerrar"));
  await user.keyboard("{Escape}");
  await act(async () => {
    await new Promise(requestAnimationFrame);
  });
  expect(onClose).not.toHaveBeenCalled();
  expect(service.withdraw).toHaveBeenCalledTimes(1);
  await act(async () => {
    resolveWrite(withdrawal);
  });
});
