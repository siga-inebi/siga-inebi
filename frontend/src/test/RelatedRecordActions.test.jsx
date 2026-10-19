import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

const service = vi.hoisted(() => ({
  listHealthNotesPage: vi.fn(),
  listObservationsPage: vi.fn(),
  listEmergencyContactsPage: vi.fn(),
  updateHealthNote: vi.fn(),
  updateObservation: vi.fn(),
  updateEmergencyContact: vi.fn(),
  deactivateHealthNote: vi.fn(),
  deactivateObservation: vi.fn(),
  deactivateEmergencyContact: vi.fn(),
}));
vi.mock("@students/studentsService.js", () => ({ studentsService: service }));

import { RelatedRecordsPanel } from "@students/StudentRecordPanels.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const student = { public_id: "student-demo" };
const row = {
  public_id: "record-demo",
  content: "Salud sintetica",
  description: "Observacion sintetica",
  name: "Contacto sintetico",
  phone_number: "5550000",
  relationship_label: "Familiar",
  recorded_on: "2026-01-01",
  observed_on: "2026-01-02",
  author: "autor-demo",
  is_active: true,
  actions: { edit: true, deactivate: true },
};
const page = (results, count = results.length) => ({ results, count });
const cases = [
  [
    "health",
    "nota de salud",
    "listHealthNotesPage",
    "updateHealthNote",
    "deactivateHealthNote",
    "Información de salud",
    "content",
  ],
  [
    "observations",
    "observación",
    "listObservationsPage",
    "updateObservation",
    "deactivateObservation",
    "Descripción",
    "description",
  ],
  [
    "contacts",
    "contacto de emergencia",
    "listEmergencyContactsPage",
    "updateEmergencyContact",
    "deactivateEmergencyContact",
    "Nombre",
    "name",
  ],
];

beforeEach(() => {
  for (const mock of Object.values(service))
    mock.mockReset().mockResolvedValue({});
  for (const method of [
    "listHealthNotesPage",
    "listObservationsPage",
    "listEmergencyContactsPage",
  ])
    service[method].mockResolvedValue(page([row]));
});

test.each(cases)(
  "edita %s con error y reintento sin enviar metadatos",
  async (kind, label, load, update, deactivate, fieldLabel, field) => {
    service[update].mockRejectedValueOnce(new Error("No se pudo corregir"));
    const user = userEvent.setup();
    renderWithRouter(
      <RelatedRecordsPanel student={student} kind={kind} onBusy={vi.fn()} />
    );
    await user.click(
      await screen.findByRole("button", { name: `Editar ${label}` })
    );
    expect(screen.getByRole("heading")).toHaveFocus();
    const input = screen.getByLabelText(new RegExp(fieldLabel));
    await user.clear(input);
    await user.type(input, "Correccion sintetica");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await screen.findByText("No se pudo corregir");
    expect(input).toHaveValue("Correccion sintetica");
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
    await screen.findByText("Registro actualizado.");
    const payload =
      kind === "contacts"
        ? {
            name: "Correccion sintetica",
            phone_number: row.phone_number,
            relationship_label: row.relationship_label,
          }
        : { [field]: "Correccion sintetica" };
    expect(service[update]).toHaveBeenLastCalledWith("record-demo", payload);
    expect(service[load]).toHaveBeenLastCalledWith(
      "student-demo",
      expect.objectContaining({ page: 1, include_inactive: false })
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  }
);

test.each(cases)(
  "desactiva %s con confirmacion y permite consultar el historial",
  async (kind, label, load, update, deactivate, fieldLabel, field) => {
    let active = true;
    service[deactivate].mockImplementation(async () => {
      active = false;
    });
    service[load].mockImplementation(async (_id, params) =>
      page(
        active
          ? [row]
          : params.include_inactive
            ? [
                {
                  ...row,
                  is_active: false,
                  actions: { edit: true, deactivate: false },
                },
              ]
            : []
      )
    );
    const user = userEvent.setup();
    renderWithRouter(
      <RelatedRecordsPanel student={student} kind={kind} onBusy={vi.fn()} />
    );
    await user.click(
      await screen.findByRole("button", { name: `Desactivar ${label}` })
    );
    expect(service[deactivate]).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(service[deactivate]).not.toHaveBeenCalled();
    await user.click(
      screen.getByRole("button", { name: `Desactivar ${label}` })
    );
    await user.click(
      screen.getByRole("button", { name: "Confirmar desactivación" })
    );
    await screen.findByText(
      "Registro desactivado. Se conserva en el historial."
    );
    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: `Desactivar ${label}` })
      ).not.toBeInTheDocument()
    );
    expect(service[deactivate]).toHaveBeenCalledExactlyOnceWith("record-demo");
    await user.click(screen.getByLabelText("Mostrar desactivados"));
    await screen.findByText("Desactivado");
    expect(
      screen.getByText(
        kind === "contacts"
          ? `${row.name} · ${row.relationship_label}`
          : row[field]
      )
    ).toBeInTheDocument();
    expect(service[load]).toHaveBeenLastCalledWith(
      "student-demo",
      expect.objectContaining({ page: 1, include_inactive: true })
    );
    expect(
      screen.queryByRole("button", { name: `Desactivar ${label}` })
    ).not.toBeInTheDocument();
  }
);

test("pagina historial en servidor y conserva filtro al corregir desde pagina dos", async () => {
  service.listHealthNotesPage.mockImplementation(async (_id, params) =>
    page(
      [
        {
          ...row,
          public_id: `record-${params.page}`,
          content: `Historico ${params.page}`,
          is_active: false,
          actions: { edit: true, deactivate: false },
        },
      ],
      26
    )
  );
  const user = userEvent.setup();
  renderWithRouter(
    <RelatedRecordsPanel student={student} kind="health" onBusy={vi.fn()} />
  );
  await screen.findByText("Historico 1");
  await user.click(screen.getByLabelText("Mostrar desactivados"));
  await waitFor(() =>
    expect(service.listHealthNotesPage).toHaveBeenLastCalledWith(
      "student-demo",
      expect.objectContaining({ page: 1, include_inactive: true })
    )
  );
  await user.click(screen.getByRole("button", { name: "Siguiente" }));
  await screen.findByText("Historico 2");
  await user.click(
    screen.getByRole("button", { name: "Editar nota de salud" })
  );
  expect(screen.getByLabelText("Mostrar desactivados")).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
  await screen.findByText("Registro actualizado.");
  expect(service.updateHealthNote).toHaveBeenCalledWith("record-2", {
    content: "Historico 2",
  });
  expect(service.listHealthNotesPage).toHaveBeenLastCalledWith(
    "student-demo",
    expect.objectContaining({ page: 1, include_inactive: true })
  );
});

test("capacidades de solo lectura ocultan las acciones E6", async () => {
  service.listHealthNotesPage.mockResolvedValue(
    page([{ ...row, actions: { edit: false, deactivate: false } }])
  );
  renderWithRouter(
    <RelatedRecordsPanel student={student} kind="health" onBusy={vi.fn()} />
  );
  await screen.findByText(row.content);
  expect(
    screen.queryByRole("button", { name: "Editar nota de salud" })
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Desactivar nota de salud" })
  ).not.toBeInTheDocument();
});

test("bloquea doble envio, filtro y navegacion mientras desactiva", async () => {
  let resolve;
  service.deactivateHealthNote.mockReturnValue(
    new Promise((done) => {
      resolve = done;
    })
  );
  const busy = vi.fn();
  const user = userEvent.setup();
  renderWithRouter(
    <RelatedRecordsPanel student={student} kind="health" onBusy={busy} />
  );
  await user.click(
    await screen.findByRole("button", { name: "Desactivar nota de salud" })
  );
  await user.click(
    screen.getByRole("button", { name: "Confirmar desactivación" })
  );
  expect(screen.getByRole("button", { name: "Guardando…" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Cancelar" })).toBeDisabled();
  expect(screen.getByLabelText("Mostrar desactivados")).toBeDisabled();
  expect(busy).toHaveBeenCalledWith(true);
  expect(service.deactivateHealthNote).toHaveBeenCalledTimes(1);
  await act(async () => resolve(null));
  await waitFor(() => expect(busy).toHaveBeenLastCalledWith(false));
});

test("un rechazo al desactivar conserva la confirmacion sin anunciar exito", async () => {
  service.deactivateHealthNote.mockRejectedValue(
    new Error("Sin permiso de escritura")
  );
  const user = userEvent.setup();
  renderWithRouter(
    <RelatedRecordsPanel student={student} kind="health" onBusy={vi.fn()} />
  );
  await user.click(
    await screen.findByRole("button", { name: "Desactivar nota de salud" })
  );
  await user.click(
    screen.getByRole("button", { name: "Confirmar desactivación" })
  );
  await screen.findByText("Sin permiso de escritura");
  expect(
    screen.getByRole("button", { name: "Confirmar desactivación" })
  ).toBeEnabled();
  expect(
    screen.queryByText("Registro desactivado. Se conserva en el historial.")
  ).not.toBeInTheDocument();
  expect(service.listHealthNotesPage).toHaveBeenCalledTimes(1);
});
