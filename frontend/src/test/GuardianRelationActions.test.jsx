import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

const service = vi.hoisted(() => ({
  listRecordGuardians: vi.fn(),
  updateGuardianRelation: vi.fn(),
  makeGuardianRelationPrimary: vi.fn(),
  endGuardianRelation: vi.fn(),
}));
vi.mock("@students/studentsService.js", () => ({ studentsService: service }));

import { GuardiansPanel } from "@students/StudentRecordPanels.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const student = { id: 1, public_id: "student-demo" };
const primary = {
  id: 11,
  relationship_label: "Madre",
  is_primary: true,
  is_active: true,
  starts_at: "2026-01-01",
  ends_at: null,
  guardian_detail: { person: { first_name: "Ana", last_name: "Demo" } },
  actions: {
    edit: true,
    make_primary: false,
    end: true,
    offers_replacement: true,
  },
};
const secondary = {
  ...primary,
  id: 12,
  is_primary: false,
  relationship_label: "Padre",
  guardian_detail: { person: { first_name: "Jose", last_name: "Demo" } },
  actions: {
    edit: true,
    make_primary: true,
    end: true,
    offers_replacement: false,
  },
};
const page = (results, count = results.length) => ({ results, count });
beforeEach(() => {
  for (const mock of Object.values(service))
    mock.mockReset().mockResolvedValue({});
  service.listRecordGuardians.mockResolvedValue(page([primary]));
});

test("corrige parentesco en linea, conserva borrador tras error y refresca pagina uno", async () => {
  service.updateGuardianRelation.mockRejectedValueOnce(
    new Error("No se pudo guardar")
  );
  const user = userEvent.setup();
  renderWithRouter(<GuardiansPanel student={student} onBusy={vi.fn()} />);
  await user.click(
    await screen.findByRole("button", { name: "Editar vínculo" })
  );
  expect(
    screen.getByRole("heading", { name: "Editar vínculo: Ana Demo" })
  ).toHaveFocus();
  const input = screen.getByLabelText(/Parentesco o responsabilidad/);
  await user.clear(input);
  await user.type(input, "Responsable");
  await user.click(screen.getByRole("button", { name: "Guardar vínculo" }));
  await screen.findByText("No se pudo guardar");
  expect(input).toHaveValue("Responsable");
  await user.click(screen.getByRole("button", { name: "Guardar vínculo" }));
  await screen.findByText("Vínculo actualizado.");
  expect(service.updateGuardianRelation).toHaveBeenLastCalledWith(11, {
    relationship_label: "Responsable",
  });
  expect(service.listRecordGuardians).toHaveBeenLastCalledWith(
    "student-demo",
    expect.objectContaining({ page: 1 })
  );
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("cambiar principal requiere confirmacion y cancelar no escribe", async () => {
  service.listRecordGuardians.mockResolvedValue(page([secondary]));
  const user = userEvent.setup();
  renderWithRouter(<GuardiansPanel student={student} onBusy={vi.fn()} />);
  await user.click(
    await screen.findByRole("button", { name: "Marcar como principal" })
  );
  expect(service.makeGuardianRelationPrimary).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Cancelar" }));
  expect(service.makeGuardianRelationPrimary).not.toHaveBeenCalled();
  await user.click(
    screen.getByRole("button", { name: "Marcar como principal" })
  );
  await user.click(screen.getByRole("button", { name: "Confirmar principal" }));
  await screen.findByText("Encargado principal actualizado.");
  expect(service.makeGuardianRelationPrimary).toHaveBeenCalledExactlyOnceWith(
    12
  );
});

test("finaliza principal con reemplazo de pagina dos sin descargar el catalogo", async () => {
  service.listRecordGuardians.mockImplementation(async (_id, params) =>
    params.replacement_for
      ? page(params.page === 2 ? [secondary] : [], 26)
      : page([primary])
  );
  const user = userEvent.setup();
  renderWithRouter(<GuardiansPanel student={student} onBusy={vi.fn()} />);
  await user.click(
    await screen.findByRole("button", { name: "Finalizar vínculo" })
  );
  await screen.findByText("No hay otros vínculos vigentes para elegir.");
  expect(
    screen.queryByRole("button", { name: "Confirmar finalización" })
  ).not.toBeInTheDocument();
  expect(service.endGuardianRelation).not.toHaveBeenCalled();
  await user.click(screen.getAllByRole("button", { name: "Siguiente" })[0]);
  await user.click(
    await screen.findByRole("button", { name: "Elegir Jose Demo · Padre" })
  );
  expect(service.listRecordGuardians).toHaveBeenCalledWith("student-demo", {
    page: 2,
    replacement_for: 11,
  });
  await user.click(
    screen.getByRole("button", { name: "Confirmar finalización" })
  );
  await screen.findByText("Vínculo finalizado. El historial se conserva.");
  expect(service.endGuardianRelation).toHaveBeenCalledExactlyOnceWith(11, {
    replacement_relation: 12,
  });
});

test("finaliza al principal sin elegir reemplazo y el estudiante queda sin principal", async () => {
  service.listRecordGuardians.mockImplementation(async (_id, params) =>
    page(params.replacement_for ? [] : [primary])
  );
  const user = userEvent.setup();
  renderWithRouter(<GuardiansPanel student={student} onBusy={vi.fn()} />);
  await user.click(
    await screen.findByRole("button", { name: "Finalizar vínculo" })
  );
  await screen.findByText("No hay otros vínculos vigentes para elegir.");
  await user.click(
    screen.getByRole("button", { name: "Continuar sin nuevo principal" })
  );
  expect(
    screen.getByText("El estudiante quedará sin encargado principal.")
  ).toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: "Confirmar finalización" })
  );
  await screen.findByText("Vínculo finalizado. El historial se conserva.");
  expect(service.endGuardianRelation).toHaveBeenCalledExactlyOnceWith(11, {});
});

test("finaliza secundario sin reemplazo y conserva error si el servidor rechaza", async () => {
  service.listRecordGuardians.mockResolvedValue(page([secondary]));
  service.endGuardianRelation.mockRejectedValueOnce(
    new Error("La relación ya cambió")
  );
  const user = userEvent.setup();
  renderWithRouter(<GuardiansPanel student={student} onBusy={vi.fn()} />);
  await user.click(
    await screen.findByRole("button", { name: "Finalizar vínculo" })
  );
  await user.click(
    screen.getByRole("button", { name: "Confirmar finalización" })
  );
  await screen.findByText("La relación ya cambió");
  expect(service.endGuardianRelation).toHaveBeenCalledWith(12, {});
  expect(service.listRecordGuardians).toHaveBeenCalledTimes(1);
  expect(
    screen.queryByText("Vínculo finalizado. El historial se conserva.")
  ).not.toBeInTheDocument();
});

test("las capacidades del servidor ocultan acciones de solo lectura e historicas", async () => {
  service.listRecordGuardians.mockResolvedValue(
    page([
      { ...primary, actions: { edit: false, make_primary: false, end: false } },
      {
        ...secondary,
        ends_at: "2026-02-01",
        actions: { edit: true, make_primary: false, end: false },
      },
    ])
  );
  renderWithRouter(<GuardiansPanel student={student} onBusy={vi.fn()} />);
  await screen.findByText("Ana Demo");
  expect(
    screen.getAllByRole("button", { name: "Editar vínculo" })
  ).toHaveLength(1);
  expect(
    screen.queryByRole("button", { name: "Finalizar vínculo" })
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Marcar como principal" })
  ).not.toBeInTheDocument();
  expect(screen.getByText(/Relación finalizada/)).toBeInTheDocument();
});

test("bloquea doble envio y comunica operacion en curso al expediente", async () => {
  service.listRecordGuardians.mockResolvedValue(page([secondary]));
  let resolve;
  service.makeGuardianRelationPrimary.mockReturnValue(
    new Promise((done) => {
      resolve = done;
    })
  );
  const busy = vi.fn();
  const user = userEvent.setup();
  renderWithRouter(<GuardiansPanel student={student} onBusy={busy} />);
  await user.click(
    await screen.findByRole("button", { name: "Marcar como principal" })
  );
  await user.click(screen.getByRole("button", { name: "Confirmar principal" }));
  expect(screen.getByRole("button", { name: "Guardando…" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Cancelar" })).toBeDisabled();
  expect(busy).toHaveBeenCalledWith(true);
  expect(service.makeGuardianRelationPrimary).toHaveBeenCalledTimes(1);
  await act(async () => resolve({}));
  await waitFor(() => expect(busy).toHaveBeenLastCalledWith(false));
});
