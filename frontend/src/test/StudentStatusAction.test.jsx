import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
const mocks = vi.hoisted(() => ({
  getRecordStatus: vi.fn(),
  changeRecordStatus: vi.fn(),
}));
vi.mock("@students/studentsService.js", () => ({ studentsService: mocks }));
import { StudentStatusAction } from "@students/StudentStatusAction.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
const student = { public_id: "student-1", status: "active" };
const context = {
  status: "active",
  can_change: true,
  has_active_enrolment: true,
  warnings: [],
  last_change: null,
  options: [
    { value: "active", label: "Activo" },
    { value: "withdrawn", label: "Retirado" },
  ],
};
const changed = vi.fn();
beforeEach(() => {
  vi.clearAllMocks();
  mocks.getRecordStatus.mockReset().mockResolvedValue(context);
  mocks.changeRecordStatus.mockReset().mockResolvedValue({
    ...context,
    status: "withdrawn",
    last_change: {
      previous_status: "active",
      status: "withdrawn",
      actor_label: "operador.demo",
      changed_at: "2026-10-18T15:00:00Z",
    },
  });
});
function renderAction() {
  return renderWithRouter(
    <StudentStatusAction student={student} onChanged={changed} />
  );
}
async function review(user) {
  await user.click(
    await screen.findByRole("button", { name: "Cambiar estado" })
  );
  await user.click(screen.getByLabelText("Nuevo estado"));
  await user.click(screen.getByRole("option", { name: "Retirado" }));
  await user.click(screen.getByRole("button", { name: "Revisar cambio" }));
  await screen.findByRole("heading", { name: "Confirmar cambio de estado" });
}

test("solo lectura muestra trazabilidad sin accion de escritura", async () => {
  mocks.getRecordStatus.mockResolvedValue({ ...context, can_change: false });
  renderAction();
  await screen.findByText("Sin cambios manuales de estado registrados.");
  expect(
    screen.queryByRole("button", { name: "Cambiar estado" })
  ).not.toBeInTheDocument();
});

test("consulta el aviso del servidor, confirma y muestra autor/fecha", async () => {
  mocks.getRecordStatus.mockResolvedValueOnce(context).mockResolvedValueOnce({
    ...context,
    warnings: ["Existe una matrícula vigente."],
  });
  const user = userEvent.setup();
  renderAction();
  await review(user);
  expect(mocks.getRecordStatus).toHaveBeenLastCalledWith("student-1", {
    status: "withdrawn",
  });
  expect(screen.getByText("Existe una matrícula vigente.")).toBeInTheDocument();
  expect(mocks.changeRecordStatus).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Confirmar cambio" }));
  await screen.findByText("Estado del expediente actualizado.");
  expect(mocks.changeRecordStatus).toHaveBeenCalledExactlyOnceWith(
    "student-1",
    { status: "withdrawn", expected_status: "active" }
  );
  expect(changed).toHaveBeenCalledWith("withdrawn");
  expect(
    screen.getByText(/Último cambio manual de estado registrado: operador.demo/)
  ).toBeInTheDocument();
});

test("cancelar la confirmacion no cambia estado", async () => {
  const user = userEvent.setup();
  renderAction();
  await review(user);
  await user.click(screen.getByRole("button", { name: "Cancelar" }));
  expect(mocks.changeRecordStatus).not.toHaveBeenCalled();
});

test("un rechazo mantiene la confirmacion y permite reintentar", async () => {
  mocks.changeRecordStatus.mockRejectedValueOnce(
    new Error("El estado cambió, recargue.")
  );
  const user = userEvent.setup();
  renderAction();
  await review(user);
  await user.click(screen.getByRole("button", { name: "Confirmar cambio" }));
  await screen.findByText("El estado cambió, recargue.");
  expect(changed).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Confirmar cambio" }));
  await waitFor(() => expect(changed).toHaveBeenCalledOnce());
});

test("bloquea doble envio y cancelacion durante escritura", async () => {
  let resolve;
  mocks.changeRecordStatus.mockImplementationOnce(
    () =>
      new Promise((done) => {
        resolve = done;
      })
  );
  const user = userEvent.setup();
  renderAction();
  await review(user);
  await user.dblClick(screen.getByRole("button", { name: "Confirmar cambio" }));
  expect(mocks.changeRecordStatus).toHaveBeenCalledOnce();
  expect(screen.getByRole("button", { name: "Cancelar" })).toBeDisabled();
  resolve({ ...context, status: "withdrawn" });
  await screen.findByText("Estado del expediente actualizado.");
});

test("si falla la consulta no ofrece cambio y permite reintentar", async () => {
  mocks.getRecordStatus.mockRejectedValueOnce(new Error("Consulta fallida"));
  const user = userEvent.setup();
  renderAction();
  await screen.findByText("Consulta fallida");
  expect(
    screen.queryByRole("button", { name: "Cambiar estado" })
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Reintentar consulta" }));
  await screen.findByRole("button", { name: "Cambiar estado" });
});
