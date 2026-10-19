import { screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

const service = vi.hoisted(() => ({
  listTemplates: vi.fn(),
  listTypes: vi.fn(),
  listTemplateIssuanceUses: vi.fn(),
  createTemplate: vi.fn(),
  updateTemplate: vi.fn(),
  deactivateTemplate: vi.fn(),
  previewTemplate: vi.fn(),
}));
vi.mock("@documents/documentsService.js", async () => ({
  ...(await vi.importActual("@documents/documentsService.js")),
  documentsService: service,
}));
import { TemplatesPage } from "@documents/TemplatesPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const ORIGINAL = {
  public_id: "original",
  name: "Original",
  code: "ORIG",
  kind: "report",
  issuance_use: "study_certificate",
  content: "{{student.code}}",
  is_active: true,
};
const USES = [
  {
    code: "enrolment_certificate",
    label: "Constancia de inscripción",
    active_template: null,
    uses_fallback: true,
  },
  {
    code: "study_certificate",
    label: "Certificado de estudios",
    active_template: { public_id: "original", name: "Original" },
    uses_fallback: false,
  },
];
beforeEach(() => {
  Object.values(service).forEach((mock) => mock.mockReset());
  service.listTemplates.mockResolvedValue({ count: 1, results: [ORIGINAL] });
  service.listTypes.mockResolvedValue({
    results: [{ code: "report", label: "Reporte" }],
  });
  service.listTemplateIssuanceUses.mockResolvedValue(USES);
  service.createTemplate.mockResolvedValue({ public_id: "new" });
});

test("editing preserves the use and omits the immutable code", async () => {
  const user = userEvent.setup();
  renderWithRouter(<TemplatesPage />);
  await screen.findByText("Original");
  await user.click(screen.getByRole("button", { name: "Editar" }));
  const dialog = await screen.findByRole("dialog", { name: "Editar Original" });
  await waitFor(() =>
    expect(
      within(dialog).getByRole("button", { name: "Guardar version" })
    ).toBeEnabled()
  );
  expect(within(dialog).queryByLabelText(/^Codigo/)).not.toBeInTheDocument();
  expect(within(dialog).queryByRole("checkbox")).not.toBeInTheDocument();
  await user.click(
    within(dialog).getByRole("button", { name: "Guardar version" })
  );
  expect(service.updateTemplate).toHaveBeenCalledWith(
    "original",
    expect.objectContaining({ issuance_use: "study_certificate" })
  );
  expect(service.updateTemplate.mock.calls[0][1]).not.toHaveProperty("code");
});

test("availability failure prevents saving and can be retried without losing input", async () => {
  const user = userEvent.setup();
  renderWithRouter(<TemplatesPage />);
  await screen.findByText("Original");
  service.listTemplateIssuanceUses.mockRejectedValueOnce(
    new Error("Disponibilidad no disponible")
  );
  await user.click(screen.getByRole("button", { name: "Nueva plantilla" }));
  const dialog = await screen.findByRole("dialog", {
    name: "Nueva plantilla documental",
  });
  await within(dialog).findByText("Disponibilidad no disponible");
  await user.type(within(dialog).getByLabelText(/^Nombre/), "Conservar");
  expect(
    within(dialog).getByRole("button", { name: "Crear plantilla" })
  ).toBeDisabled();
  await user.click(within(dialog).getByRole("button", { name: "Reintentar" }));
  await waitFor(() =>
    expect(
      within(dialog).getByRole("button", { name: "Crear plantilla" })
    ).toBeEnabled()
  );
  expect(within(dialog).getByLabelText(/^Nombre/)).toHaveValue("Conservar");
  expect(service.createTemplate).not.toHaveBeenCalled();
});

async function newForm(user) {
  renderWithRouter(<TemplatesPage />);
  await screen.findByText("Original");
  await user.click(screen.getByRole("button", { name: "Nueva plantilla" }));
  const dialog = await screen.findByRole("dialog", {
    name: "Nueva plantilla documental",
  });
  await user.type(within(dialog).getByLabelText(/^Nombre/), "Nueva");
  await user.type(within(dialog).getByLabelText(/^Codigo/), "NUEVA");
  await user.click(
    within(dialog).getByRole("combobox", { name: "Se usa para" })
  );
  await user.click(
    await screen.findByRole("option", { name: /Certificado de estudios/ })
  );
  return dialog;
}

test("shows explicit use and warns when an emission uses default text", async () => {
  renderWithRouter(<TemplatesPage />);
  expect(
    await screen.findByText(
      /Constancia de inscripción usa el texto por defecto/i
    )
  ).toBeInTheDocument();
  expect(screen.getByText("Certificado de estudios")).toBeInTheDocument();
  expect(service.listTemplateIssuanceUses).toHaveBeenCalledTimes(1);
});

test("requires confirmation and sends the exact replaced UUID", async () => {
  const user = userEvent.setup();
  const dialog = await newForm(user);
  await user.click(
    within(dialog).getByRole("button", { name: "Crear plantilla" })
  );
  expect(service.createTemplate).not.toHaveBeenCalled();
  await user.click(
    within(dialog).getByRole("checkbox", { name: /Reemplazar.*Original/ })
  );
  await user.click(
    within(dialog).getByRole("button", { name: "Crear plantilla" })
  );
  expect(service.createTemplate).toHaveBeenCalledWith(
    expect.objectContaining({
      issuance_use: "study_certificate",
      replaces_template_id: "original",
      kind: "report",
    })
  );
});

test("stale confirmation refreshes availability, keeps draft and requires a new confirmation", async () => {
  const user = userEvent.setup();
  const dialog = await newForm(user);
  await user.type(
    within(dialog).getByLabelText("Contenido de la plantilla"),
    "Borrador conservado"
  );
  await user.click(
    within(dialog).getByRole("checkbox", { name: /Reemplazar.*Original/ })
  );
  service.createTemplate.mockRejectedValueOnce(
    new Error("La plantilla activa cambio")
  );
  service.listTemplateIssuanceUses.mockResolvedValue([
    USES[0],
    { ...USES[1], active_template: { public_id: "other", name: "Otra" } },
  ]);
  await user.click(
    within(dialog).getByRole("button", { name: "Crear plantilla" })
  );
  const checkbox = await within(dialog).findByRole("checkbox", {
    name: /Reemplazar.*Otra/,
  });
  expect(checkbox).not.toBeChecked();
  expect(
    within(dialog).getByLabelText("Contenido de la plantilla")
  ).toHaveValue("Borrador conservado");
  await user.click(checkbox);
  await user.click(
    within(dialog).getByRole("button", { name: "Crear plantilla" })
  );
  expect(service.createTemplate).toHaveBeenLastCalledWith(
    expect.objectContaining({
      replaces_template_id: "other",
      content: "Borrador conservado",
    })
  );
});

test("preview supplies all eight nonempty sample values without creating a version", async () => {
  service.previewTemplate.mockResolvedValue({
    content: "Sample",
    marker_count: 8,
  });
  const user = userEvent.setup();
  renderWithRouter(<TemplatesPage />);
  await screen.findByText("Original");
  await user.click(screen.getByRole("button", { name: "Vista previa" }));
  await waitFor(() => expect(service.previewTemplate).toHaveBeenCalled());
  const sample = service.previewTemplate.mock.calls[0][1];
  expect(Object.keys(sample).sort()).toEqual(
    [
      "student.full_name",
      "student.code",
      "institution.name",
      "institution.short_name",
      "academic.cycle_name",
      "academic.section_name",
      "enrolment.effective_on",
      "document.issue_date",
    ].sort()
  );
  expect(
    Object.values(sample).every(
      (value) => typeof value === "string" && value.length > 0
    )
  ).toBe(true);
  expect(service.createTemplate).not.toHaveBeenCalled();
  expect(service.updateTemplate).not.toHaveBeenCalled();
});
