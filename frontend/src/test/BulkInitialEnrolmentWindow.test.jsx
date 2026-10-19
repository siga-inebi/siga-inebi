import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

const service = vi.hoisted(() => ({
  listInitialCandidates: vi.fn(),
  bulkMatriculate: vi.fn(),
}));
vi.mock("@enrolments/enrolmentsService.js", () => ({
  enrolmentsService: service,
}));
vi.mock("@shared/catalogs/academicCatalogs.js", () => ({
  useCycleCatalog: () => ({ options: [{ value: "c1", label: "Ciclo Demo" }] }),
  useSectionCatalog: () => ({
    options: [
      { value: "a1", label: "Seccion A" },
      { value: "a2", label: "Seccion B" },
    ],
  }),
  sectionsForCycle: (options, cycle) => (cycle ? options : []),
}));

import { BulkEnrolmentWindow } from "@enrolments/BulkEnrolmentWindow.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const first = {
  public_id: "s1",
  full_name: "Alumno Uno",
  student_code: "EST-1",
};
const second = {
  public_id: "s2",
  full_name: "Alumno Dos",
  student_code: "EST-2",
};
const page = (rows, count = rows.length) => ({ results: rows, count });
const summary = (preview, statuses = ["ready"], ids = ["s1"]) => ({
  preview,
  total: ids.length,
  succeeded: statuses.filter((s) => s !== "error").length,
  failed: statuses.filter((s) => s === "error").length,
  results: ids.map((id, index) => ({
    student_id: id,
    status: statuses[index],
    enrolment_id: preview ? null : `e-${id}`,
    error: statuses[index] === "error" ? "Sin vacantes" : null,
  })),
});

beforeEach(() => {
  service.listInitialCandidates.mockReset().mockResolvedValue(page([first]));
  service.bulkMatriculate
    .mockReset()
    .mockImplementation(async (payload) =>
      summary(payload.preview, [payload.preview ? "ready" : "created"])
    );
});

async function setup() {
  const user = userEvent.setup();
  const onCreated = vi.fn();
  const onClose = vi.fn();
  renderWithRouter(
    <BulkEnrolmentWindow onCreated={onCreated} onClose={onClose} />
  );
  for (const [name, option] of [
    ["Ciclo escolar", "Ciclo Demo"],
    ["Seccion", "Seccion A"],
  ]) {
    await user.click(screen.getByRole("combobox", { name }));
    await user.click(await screen.findByRole("option", { name: option }));
  }
  await user.type(screen.getByLabelText(/Vigente desde/), "2026-02-01");
  return { user, onCreated, onClose };
}

async function selectFirst(user) {
  await user.type(
    screen.getByPlaceholderText(/Buscar por nombre o codigo/),
    "Alumno"
  );
  await user.click(await screen.findByLabelText("Alumno Uno · EST-1"));
}

test("no descarga candidatos antes de elegir contexto y escribir dos letras", async () => {
  const { user } = await setup();
  expect(service.listInitialCandidates).not.toHaveBeenCalled();
  await user.type(
    screen.getByPlaceholderText(/Buscar por nombre o codigo/),
    "A"
  );
  await screen.findByText("Escriba al menos 2 letras para buscar.");
  expect(service.listInitialCandidates).not.toHaveBeenCalled();
  await user.type(
    screen.getByPlaceholderText(/Buscar por nombre o codigo/),
    "l"
  );
  await screen.findByLabelText("Alumno Uno · EST-1");
  expect(service.listInitialCandidates).toHaveBeenLastCalledWith({
    section_id: "a1",
    page: 1,
    search: "Al",
  });
});

test("conserva selección entre páginas y usa un POST por revisión/confirmación", async () => {
  service.listInitialCandidates.mockImplementation(async ({ page: number }) =>
    page([number === 2 ? second : first], 26)
  );
  service.bulkMatriculate.mockImplementation(async (payload) =>
    summary(
      payload.preview,
      payload.student_ids.map(() => (payload.preview ? "ready" : "created")),
      payload.student_ids
    )
  );
  const { user, onCreated } = await setup();
  await selectFirst(user);
  await user.click(screen.getByRole("button", { name: "Siguiente" }));
  await user.click(await screen.findByLabelText("Alumno Dos · EST-2"));
  expect(screen.getByText("2 seleccionados de 100")).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Confirmar matrículas" })
  ).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "Vista previa" }));
  await user.click(
    await screen.findByRole("button", { name: "Confirmar matrículas" })
  );
  await waitFor(() => expect(onCreated).toHaveBeenCalledTimes(1));
  expect(service.bulkMatriculate).toHaveBeenCalledTimes(2);
  expect(service.bulkMatriculate).toHaveBeenLastCalledWith({
    section_id: "a1",
    effective_on: "2026-02-01",
    student_ids: ["s1", "s2"],
    preview: false,
  });
});

test("cambiar fecha o selección invalida la revisión anterior", async () => {
  const { user } = await setup();
  await selectFirst(user);
  await user.click(screen.getByRole("button", { name: "Vista previa" }));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Confirmar matrículas" })
    ).toBeEnabled()
  );
  await user.clear(screen.getByLabelText(/Vigente desde/));
  await user.type(screen.getByLabelText(/Vigente desde/), "2026-03-01");
  expect(
    screen.getByRole("button", { name: "Confirmar matrículas" })
  ).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "Vista previa" }));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Confirmar matrículas" })
    ).toBeEnabled()
  );
  await user.click(screen.getByLabelText("Alumno Uno · EST-1"));
  expect(
    screen.getByRole("button", { name: "Confirmar matrículas" })
  ).toBeDisabled();
});

test("conserva solo filas fallidas después de confirmar parcialmente", async () => {
  service.listInitialCandidates.mockResolvedValue(page([first, second]));
  service.bulkMatriculate.mockResolvedValueOnce(
    summary(true, ["ready", "ready"], ["s1", "s2"])
  );
  service.bulkMatriculate.mockResolvedValueOnce(
    summary(false, ["created", "error"], ["s1", "s2"])
  );
  const { user } = await setup();
  await selectFirst(user);
  await user.click(screen.getByLabelText("Alumno Dos · EST-2"));
  await user.click(screen.getByRole("button", { name: "Vista previa" }));
  await user.click(
    await screen.findByRole("button", { name: "Confirmar matrículas" })
  );
  await screen.findByText(/Alumno Dos · EST-2: No procesada/);
  expect(screen.getByText("1 seleccionados de 100")).toBeInTheDocument();
  expect(screen.getByLabelText("Alumno Dos · EST-2")).toBeChecked();
  expect(screen.getByLabelText("Alumno Uno · EST-1")).not.toBeChecked();
});

test("error de transporte conserva selección y exige revisión nueva", async () => {
  service.bulkMatriculate.mockRejectedValueOnce(new Error("Sin conexión"));
  const { user } = await setup();
  await selectFirst(user);
  await user.click(screen.getByRole("button", { name: "Vista previa" }));
  await screen.findByText("Sin conexión");
  expect(screen.getByLabelText("Alumno Uno · EST-1")).toBeChecked();
  expect(
    screen.getByRole("button", { name: "Confirmar matrículas" })
  ).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "Vista previa" }));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Confirmar matrículas" })
    ).toBeEnabled()
  );
});

test("bloquea cierre y cambios mientras procesa", async () => {
  let finish;
  service.bulkMatriculate.mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      })
  );
  const { user, onClose } = await setup();
  await selectFirst(user);
  await user.click(screen.getByRole("button", { name: "Vista previa" }));
  expect(
    screen.getAllByRole("button", { name: "Cerrar" }).at(-1)
  ).toBeDisabled();
  expect(
    screen.getByRole("button", { name: "Limpiar búsqueda" })
  ).toBeDisabled();
  await user.keyboard("{Escape}");
  expect(onClose).not.toHaveBeenCalled();
  expect(screen.getByLabelText(/Vigente desde/)).toBeDisabled();
  finish(summary(true));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Confirmar matrículas" })
    ).toBeEnabled()
  );
});

test("un fallo de búsqueda ofrece reintento sin descartar el contexto", async () => {
  service.listInitialCandidates.mockRejectedValueOnce(
    new Error("No se pudo buscar")
  );
  const { user } = await setup();
  await user.type(
    screen.getByPlaceholderText(/Buscar por nombre o codigo/),
    "Alumno"
  );
  await user.click(
    await screen.findByRole("button", { name: "Reintentar búsqueda" })
  );
  await screen.findByLabelText("Alumno Uno · EST-1");
  expect(screen.getByLabelText(/Vigente desde/)).toHaveValue("2026-02-01");
});
