import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

const service = vi.hoisted(() => ({
  transferIn: vi.fn(),
  transferOut: vi.fn(),
  listMovements: vi.fn(),
}));
const students = vi.hoisted(() => ({ listPage: vi.fn() }));
const academic = vi.hoisted(() => ({ listSections: vi.fn() }));
const cycleCatalog = vi.hoisted(() => vi.fn());
vi.mock("@enrolments/enrolmentsService.js", async () => ({
  ...(await vi.importActual("@enrolments/enrolmentsService.js")),
  enrolmentsService: service,
}));
vi.mock("@students/studentsService.js", () => ({ studentsService: students }));
vi.mock("@academics/academicsService.js", async () => ({
  ...(await vi.importActual("@academics/academicsService.js")),
  academicsService: academic,
}));
vi.mock("@shared/catalogs/academicCatalogs.js", async () => ({
  ...(await vi.importActual("@shared/catalogs/academicCatalogs.js")),
  useCycleCatalog: cycleCatalog,
}));

import { StudentTransferWindow } from "@enrolments/StudentTransferWindow.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const source = {
  public_id: "enr-1",
  student_id: "stu-1",
  academic_cycle_id: "cycle-1",
  grade_id: "grade-1",
  section_id: "section-1",
};
const ana = {
  public_id: "stu-1",
  student_code: "EST-1",
  person: { first_name: "Ana", last_name: "Demo" },
};
const bea = {
  ...ana,
  public_id: "stu-2",
  student_code: "EST-2",
  person: { first_name: "Bea", last_name: "Demo" },
  status: "transferred",
};
const movement = {
  public_id: "move-1",
  movement_type: "transfer_out",
  reason: "Cambio de instituto",
  effective_on: "2026-03-01",
  created_at: "2026-03-02T12:00:00Z",
  annulment: null,
};
const paged = (results, count = results.length) => ({
  count,
  results,
  next: null,
});

beforeEach(() => {
  students.listPage
    .mockReset()
    .mockImplementation(({ page }) =>
      Promise.resolve(paged(page === 2 ? [bea] : [ana], 26))
    );
  academic.listSections.mockReset().mockResolvedValue(
    paged([
      {
        public_id: "section-2",
        name: "B",
        grade: { public_id: "grade-2", name: "Segundo" },
        shift: { public_id: "shift-2", name: "Matutina" },
      },
    ])
  );
  cycleCatalog.mockReset().mockReturnValue({
    options: [
      { value: "cycle-1", label: "2026" },
      { value: "cycle-2", label: "2025" },
    ],
    loading: false,
    error: "",
  });
  service.transferIn
    .mockReset()
    .mockResolvedValue({ ...movement, movement_type: "transfer_in" });
  service.transferOut.mockReset().mockResolvedValue(movement);
  service.listMovements.mockReset().mockResolvedValue(paged([movement]));
});

function mount(direction = "out") {
  const onChanged = vi.fn();
  const onClose = vi.fn();
  renderWithRouter(
    <StudentTransferWindow
      direction={direction}
      enrolment={direction === "out" ? source : undefined}
      studentLabel="Ana Demo · EST-1"
      onChanged={onChanged}
      onClose={onClose}
    />
  );
  return { user: userEvent.setup(), onChanged, onClose };
}

async function choose(user, label, option) {
  await user.click(screen.getByRole("combobox", { name: label }));
  await user.click(await screen.findByRole("option", { name: option }));
}

async function selectIncomingStudent(user, page = 1) {
  await user.type(
    screen.getByPlaceholderText("Buscar estudiante por nombre o código"),
    "Demo"
  );
  await screen.findByRole("button", { name: "Seleccionar EST-1" });
  if (page === 2)
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
  await user.click(
    await screen.findByRole("button", {
      name: page === 2 ? "Seleccionar EST-2" : "Seleccionar EST-1",
    })
  );
}

async function incomingReady() {
  const state = mount("in");
  expect(students.listPage).not.toHaveBeenCalled();
  expect(screen.getByRole("tab", { name: "Historial" })).toBeDisabled();
  await selectIncomingStudent(state.user, 2);
  await choose(state.user, "Ciclo de destino", "2026");
  await choose(state.user, "Sección de destino", "Segundo · B · Matutina");
  await state.user.type(screen.getByLabelText("Vigente desde"), "2026-03-01");
  return state;
}

test("egreso usa la matrícula seleccionada, motivo opcional y confirmación explícita", async () => {
  const { user, onChanged } = mount();
  expect(students.listPage).not.toHaveBeenCalled();
  expect(cycleCatalog).not.toHaveBeenCalled();
  expect(academic.listSections).not.toHaveBeenCalled();
  expect(screen.getByText(/El egreso cierra la matrícula/)).toBeInTheDocument();
  await user.type(screen.getByLabelText("Vigente desde"), "2026-03-01");
  await user.click(screen.getByRole("button", { name: "Revisar traslado" }));
  expect(service.transferOut).not.toHaveBeenCalled();
  expect(screen.getAllByRole("dialog")).toHaveLength(1);
  await user.click(screen.getByRole("button", { name: "Confirmar egreso" }));
  expect(
    await screen.findByRole("cell", { name: "Traslado de egreso" })
  ).toBeInTheDocument();
  expect(service.transferOut).toHaveBeenCalledWith("enr-1", {
    effective_on: "2026-03-01",
    reason: "",
  });
  expect(onChanged).toHaveBeenCalledTimes(1);
  expect(
    screen.getByRole("tab", { name: "Registrar traslado" })
  ).toBeDisabled();
});

test("ingreso busca por páginas y deriva grado y jornada de la sección remota", async () => {
  const { user, onChanged } = await incomingReady();
  expect(students.listPage).toHaveBeenLastCalledWith({
    page: 2,
    search: "Demo",
  });
  expect(academic.listSections).toHaveBeenCalledWith(
    expect.objectContaining({ academic_cycle_id: "cycle-1" })
  );
  expect(screen.getByText("Bea Demo · EST-2")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Revisar traslado" }));
  expect(service.transferIn).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Confirmar ingreso" }));
  await waitFor(() => expect(onChanged).toHaveBeenCalledTimes(1));
  expect(service.transferIn).toHaveBeenCalledWith({
    student_id: "stu-2",
    academic_cycle_id: "cycle-1",
    grade_id: "grade-2",
    shift_id: "shift-2",
    section_id: "section-2",
    effective_on: "2026-03-01",
  });
  expect(service.listMovements).toHaveBeenLastCalledWith(
    expect.objectContaining({ student_id: "stu-2" })
  );
});

test("cambiar ciclo limpia sección e invalida la revisión del ingreso", async () => {
  const { user } = await incomingReady();
  await user.click(screen.getByRole("button", { name: "Revisar traslado" }));
  expect(
    screen.getByRole("button", { name: "Confirmar ingreso" })
  ).toBeInTheDocument();
  await choose(user, "Ciclo de destino", "2025");
  expect(
    screen.queryByRole("button", { name: "Confirmar ingreso" })
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Revisar traslado" }));
  expect(
    await screen.findByText("Seleccione ciclo y sección de destino.")
  ).toBeInTheDocument();
  expect(service.transferIn).not.toHaveBeenCalled();
});

test("cambiar estudiante descarta la revisión y evita usar datos del expediente anterior", async () => {
  const { user } = await incomingReady();
  await user.click(screen.getByRole("button", { name: "Revisar traslado" }));
  await user.click(screen.getByRole("button", { name: "Cambiar estudiante" }));
  await selectIncomingStudent(user);
  expect(
    screen.queryByRole("button", { name: "Confirmar ingreso" })
  ).not.toBeInTheDocument();
  expect(screen.getByLabelText("Vigente desde")).toHaveValue("");
  expect(service.transferIn).not.toHaveBeenCalled();
});

test("fecha obligatoria y cambios posteriores requieren otra revisión", async () => {
  const { user } = mount();
  await user.click(screen.getByRole("button", { name: "Revisar traslado" }));
  expect(
    await screen.findByText("Indique la fecha de vigencia.")
  ).toBeInTheDocument();
  await user.type(screen.getByLabelText("Vigente desde"), "2026-03-01");
  await user.click(screen.getByRole("button", { name: "Revisar traslado" }));
  await user.type(
    screen.getByLabelText("Motivo del egreso (opcional)"),
    "Cambio familiar"
  );
  expect(
    screen.queryByRole("button", { name: "Confirmar egreso" })
  ).not.toBeInTheDocument();
  expect(service.transferOut).not.toHaveBeenCalled();
});

test.each([
  "El actor no tiene alcance.",
  "Los traslados con fecha futura permanecen pendientes de definicion.",
])("rechazo preserva fecha y motivo: %s", async (message) => {
  const { user } = mount();
  service.transferOut.mockRejectedValueOnce(new Error(message));
  await user.type(screen.getByLabelText("Vigente desde"), "2026-03-01");
  await user.type(
    screen.getByLabelText("Motivo del egreso (opcional)"),
    "Conservar motivo"
  );
  await user.click(screen.getByRole("button", { name: "Revisar traslado" }));
  await user.click(screen.getByRole("button", { name: "Confirmar egreso" }));
  expect(await screen.findByText(message)).toBeInTheDocument();
  expect(screen.getByLabelText("Vigente desde")).toHaveValue("2026-03-01");
  expect(screen.getByLabelText("Motivo del egreso (opcional)")).toHaveValue(
    "Conservar motivo"
  );
  expect(
    screen.queryByRole("button", { name: "Confirmar egreso" })
  ).not.toBeInTheDocument();
  expect(service.transferOut).toHaveBeenCalledTimes(1);
});

test("bloquea cierre y doble envío durante la confirmación del ingreso", async () => {
  const { user, onClose } = await incomingReady();
  let finish;
  service.transferIn.mockReturnValueOnce(
    new Promise((resolve) => {
      finish = resolve;
    })
  );
  await user.click(screen.getByRole("button", { name: "Revisar traslado" }));
  await user.click(screen.getByRole("button", { name: "Confirmar ingreso" }));
  expect(screen.getByRole("button", { name: "Procesando…" })).toBeDisabled();
  expect(screen.getByRole("tab", { name: "Historial" })).toBeDisabled();
  await user.click(screen.getByLabelText("Cerrar"));
  await user.keyboard("{Escape}");
  await act(async () => {
    await new Promise(requestAnimationFrame);
  });
  expect(onClose).not.toHaveBeenCalled();
  expect(service.transferIn).toHaveBeenCalledTimes(1);
  await act(async () => {
    finish(movement);
  });
});

test("historial se pagina por estudiante sin ofrecer anulación de traslados", async () => {
  service.listMovements.mockImplementation(({ page }) =>
    Promise.resolve(
      paged(
        [
          {
            ...movement,
            reason: page === 2 ? "Segunda evidencia" : "Primera evidencia",
          },
        ],
        26
      )
    )
  );
  const { user } = mount();
  await user.click(screen.getByRole("tab", { name: "Historial" }));
  await screen.findByText("Primera evidencia");
  await user.click(screen.getByRole("button", { name: "Siguiente" }));
  expect(await screen.findByText("Segunda evidencia")).toBeInTheDocument();
  expect(service.listMovements).toHaveBeenLastCalledWith(
    expect.objectContaining({ page: 2, student_id: "stu-1" })
  );
  expect(
    screen.queryByRole("button", { name: "Anular movimiento" })
  ).not.toBeInTheDocument();
  expect(service.transferOut).not.toHaveBeenCalled();
});

test("búsqueda fallida permite reintentar sin descargar el padrón", async () => {
  students.listPage.mockRejectedValueOnce(
    new Error("No se pudo consultar estudiantes.")
  );
  const { user } = mount("in");
  await user.type(
    screen.getByPlaceholderText("Buscar estudiante por nombre o código"),
    "Demo"
  );
  expect(
    await screen.findByText("No se pudo consultar estudiantes.")
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Reintentar búsqueda" }));
  await screen.findByRole("button", { name: "Seleccionar EST-1" });
  expect(students.listPage).toHaveBeenCalledTimes(2);
});
