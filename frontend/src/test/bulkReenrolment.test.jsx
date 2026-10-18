import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

const service = vi.hoisted(() => ({
  listReenrolmentCandidates: vi.fn(),
  bulkReenrol: vi.fn(),
}));
const academic = vi.hoisted(() => ({ listSections: vi.fn() }));
vi.mock("@enrolments/enrolmentsService.js", () => ({
  enrolmentsService: service,
}));
vi.mock("@academics/academicsService.js", () => ({
  academicsService: academic,
}));
vi.mock("@shared/catalogs/academicCatalogs.js", () => ({
  useCycleCatalog: () => ({
    options: [
      { value: "source", label: "2026" },
      { value: "target", label: "2027" },
    ],
    loading: false,
    error: "",
  }),
}));

import { BulkReenrolmentWindow } from "@enrolments/BulkReenrolmentWindow.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const ana = {
  public_id: "source-ana",
  first_name: "Ana",
  last_name: "Demo",
  student_code: "EST-1",
  grade_name: "Primero",
  section_name: "A",
};
const ines = {
  ...ana,
  public_id: "source-ines",
  first_name: "Ines",
  student_code: "EST-2",
};
const paged = (results, count = results.length) => ({
  count,
  results,
  next: null,
});
const batch = (preview = true) => ({
  preview,
  total: 1,
  succeeded: 1,
  failed: 0,
  results: [
    {
      source_enrolment_id: ana.public_id,
      status: preview ? "ready" : "created",
      error: null,
    },
  ],
});

beforeEach(() => {
  service.listReenrolmentCandidates
    .mockReset()
    .mockImplementation(({ page }) =>
      Promise.resolve(paged(page === 2 ? [ines] : [ana], 26))
    );
  service.bulkReenrol
    .mockReset()
    .mockImplementation(({ preview }) => Promise.resolve(batch(preview)));
  academic.listSections.mockReset().mockResolvedValue(
    paged([
      {
        public_id: "section",
        name: "B",
        grade: { name: "Segundo" },
        shift: { name: "Matutina" },
      },
    ])
  );
});

async function select(user, name, option) {
  await user.click(screen.getByRole("combobox", { name }));
  await user.click(await screen.findByRole("option", { name: option }));
}

async function prepare() {
  const user = userEvent.setup();
  const onCreated = vi.fn();
  const onClose = vi.fn();
  renderWithRouter(
    <BulkReenrolmentWindow onClose={onClose} onCreated={onCreated} />
  );
  expect(service.listReenrolmentCandidates).not.toHaveBeenCalled();
  expect(academic.listSections).not.toHaveBeenCalled();
  await select(user, "Ciclo de origen", "2026");
  await screen.findByRole("checkbox", { name: "Ana Demo · EST-1" });
  await select(user, "Ciclo de destino", "2027");
  await select(user, "Sección de destino", "Segundo · B · Matutina");
  await user.type(screen.getByLabelText("Vigente desde"), "2027-01-15");
  await user.click(screen.getByRole("checkbox", { name: "Ana Demo · EST-1" }));
  return { user, onCreated, onClose };
}

test("conserva selección entre páginas y envía una petición por lote con UUID de matrícula", async () => {
  const { user } = await prepare();
  expect(academic.listSections).toHaveBeenCalledWith(
    expect.objectContaining({ academic_cycle_id: "target" })
  );
  await user.click(screen.getByRole("button", { name: "Siguiente" }));
  await user.click(
    await screen.findByRole("checkbox", { name: "Ines Demo · EST-2" })
  );
  expect(service.listReenrolmentCandidates).toHaveBeenLastCalledWith({
    page: 2,
    academic_cycle_id: "source",
    search: "",
  });
  expect(
    screen.getByRole("button", { name: "Confirmar reinscripción" })
  ).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "Vista previa" }));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Confirmar reinscripción" })
    ).toBeEnabled()
  );
  expect(service.bulkReenrol).toHaveBeenCalledTimes(1);
  expect(service.bulkReenrol).toHaveBeenCalledWith({
    preview: true,
    effective_on: "2027-01-15",
    items: [
      { source_enrolment_id: "source-ana", target_section_id: "section" },
      { source_enrolment_id: "source-ines", target_section_id: "section" },
    ],
  });
});

test("búsqueda remota vuelve a la página uno y conserva la selección", async () => {
  const { user } = await prepare();
  await user.click(screen.getByRole("button", { name: "Siguiente" }));
  await screen.findByRole("checkbox", { name: "Ines Demo · EST-2" });
  await user.type(
    screen.getByPlaceholderText("Buscar estudiante por nombre o código"),
    "Ana"
  );
  await waitFor(() =>
    expect(service.listReenrolmentCandidates).toHaveBeenLastCalledWith({
      page: 1,
      academic_cycle_id: "source",
      search: "Ana",
    })
  );
  expect(
    await screen.findByRole("checkbox", { name: "Ana Demo · EST-1" })
  ).toBeChecked();
});

test.each(["fecha", "selección", "destino", "origen"])(
  "cambiar %s invalida la confirmación revisada",
  async (change) => {
    const { user } = await prepare();
    await user.click(screen.getByRole("button", { name: "Vista previa" }));
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Confirmar reinscripción" })
      ).toBeEnabled()
    );
    if (change === "fecha") {
      await user.clear(screen.getByLabelText("Vigente desde"));
      await user.type(screen.getByLabelText("Vigente desde"), "2027-01-16");
    }
    if (change === "selección")
      await user.click(
        screen.getByRole("button", { name: "Limpiar selección" })
      );
    if (change === "destino") await select(user, "Ciclo de destino", "2026");
    if (change === "origen") await select(user, "Ciclo de origen", "2027");
    expect(
      screen.getByRole("button", { name: "Confirmar reinscripción" })
    ).toBeDisabled();
    expect(service.bulkReenrol).toHaveBeenCalledTimes(1);
  }
);

test("muestra resultado parcial por persona y confirma solo tras revisar", async () => {
  const { user, onCreated } = await prepare();
  await user.click(screen.getByRole("button", { name: "Siguiente" }));
  await user.click(
    await screen.findByRole("checkbox", { name: "Ines Demo · EST-2" })
  );
  service.bulkReenrol.mockImplementation(({ preview }) =>
    Promise.resolve({
      preview,
      total: 2,
      succeeded: 1,
      failed: 1,
      results: [
        {
          source_enrolment_id: ana.public_id,
          status: preview ? "ready" : "created",
          error: null,
        },
        {
          source_enrolment_id: ines.public_id,
          status: "error",
          error: "La seccion alcanzo su cupo.",
        },
      ],
    })
  );
  await user.click(screen.getByRole("button", { name: "Vista previa" }));
  expect(
    await screen.findByText("La seccion alcanzo su cupo.")
  ).toBeInTheDocument();
  expect(onCreated).not.toHaveBeenCalled();
  await user.click(
    screen.getByRole("button", { name: "Confirmar reinscripción" })
  );
  expect(await screen.findByText("Reinscrita")).toBeInTheDocument();
  expect(
    within(screen.getAllByRole("table")[1]).getByText("Ana Demo · EST-1")
  ).toBeInTheDocument();
  expect(onCreated).toHaveBeenCalledTimes(1);
  expect(service.bulkReenrol).toHaveBeenCalledTimes(2);
  expect(service.bulkReenrol.mock.calls[1][0]).toEqual({
    ...service.bulkReenrol.mock.calls[0][0],
    preview: false,
  });
  expect(
    screen.getByRole("button", { name: "Confirmar reinscripción" })
  ).toBeDisabled();
});

test("un fallo de confirmación conserva selección y exige otra vista previa", async () => {
  const { user, onCreated } = await prepare();
  await user.click(screen.getByRole("button", { name: "Vista previa" }));
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Confirmar reinscripción" })
    ).toBeEnabled()
  );
  service.bulkReenrol.mockRejectedValueOnce(
    new Error("Se perdió la conexión.")
  );
  await user.click(
    screen.getByRole("button", { name: "Confirmar reinscripción" })
  );
  expect(await screen.findByText("Se perdió la conexión.")).toBeInTheDocument();
  expect(
    screen.getByRole("checkbox", { name: "Ana Demo · EST-1" })
  ).toBeChecked();
  expect(
    screen.getByRole("button", { name: "Confirmar reinscripción" })
  ).toBeDisabled();
  expect(onCreated).not.toHaveBeenCalled();
  service.bulkReenrol.mockResolvedValueOnce({
    ...batch(),
    results: [{ source_enrolment_id: ana.public_id, status: "existing" }],
  });
  await user.click(screen.getByRole("button", { name: "Vista previa" }));
  expect(
    await screen.findByText("Ya registrada en destino")
  ).toBeInTheDocument();
});

test("candidatos fallidos permiten reintentar sin recorrer otras páginas", async () => {
  service.listReenrolmentCandidates.mockRejectedValueOnce(
    new Error("Sin alcance disponible.")
  );
  const user = userEvent.setup();
  renderWithRouter(<BulkReenrolmentWindow onClose={vi.fn()} />);
  await select(user, "Ciclo de origen", "2026");
  expect(
    await screen.findByText("Sin alcance disponible.")
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Reintentar consulta" }));
  await screen.findByRole("checkbox", { name: "Ana Demo · EST-1" });
  expect(service.listReenrolmentCandidates).toHaveBeenCalledTimes(2);
});

test("bloquea cierre y doble envío mientras se procesa el lote", async () => {
  const { user, onClose } = await prepare();
  let resolvePreview;
  service.bulkReenrol.mockReturnValueOnce(
    new Promise((resolve) => {
      resolvePreview = resolve;
    })
  );
  await user.click(screen.getByRole("button", { name: "Vista previa" }));
  expect(screen.getByRole("button", { name: "Vista previa" })).toBeDisabled();
  expect(
    screen.getByRole("combobox", { name: "Ciclo de origen" })
  ).toHaveAttribute("aria-disabled", "true");
  await user.click(screen.getByLabelText("Cerrar"));
  await user.keyboard("{Escape}");
  await act(async () => {
    await new Promise(requestAnimationFrame);
  });
  expect(onClose).not.toHaveBeenCalled();
  expect(service.bulkReenrol).toHaveBeenCalledTimes(1);
  await act(async () => {
    resolvePreview(batch());
  });
  await user.click(screen.getByLabelText("Cerrar"));
  await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
});
