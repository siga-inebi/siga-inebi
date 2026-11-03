import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";
const mocks = vi.hoisted(() => ({
  listPage: vi.fn(),
  linkRecordGuardian: vi.fn(),
}));
vi.mock("@guardians/guardiansService.js", () => ({ guardiansService: mocks }));
vi.mock("@students/studentsService.js", () => ({ studentsService: mocks }));
import { GuardianLinkForm } from "@students/GuardianLinkForm.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const page = (results = [], count = results.length) => ({ results, count });
const guardian = {
  id: 7,
  person: { first_name: "Responsable", last_name: "Demo" },
};
const saved = vi.fn();
const cancel = vi.fn();
beforeEach(() => {
  vi.clearAllMocks();
  mocks.listPage.mockReset().mockResolvedValue(page([guardian], 30));
  mocks.linkRecordGuardian.mockReset().mockResolvedValue({ id: 1 });
});
function renderForm() {
  return renderWithRouter(
    <GuardianLinkForm
      student={{ public_id: "student-1" }}
      onSaved={saved}
      onCancel={cancel}
    />
  );
}

test("busca en servidor, vuelve a pagina 1 y conserva paginacion bajo el filtro", async () => {
  const user = userEvent.setup();
  renderForm();
  await screen.findByRole("button", { name: "Elegir Responsable Demo" });
  await user.click(screen.getByRole("button", { name: "Siguiente" }));
  await waitFor(() =>
    expect(mocks.listPage).toHaveBeenLastCalledWith({ page: 2, search: "" })
  );
  await user.type(
    screen.getByPlaceholderText("Buscar por nombre o CUI"),
    "Demo"
  );
  await user.click(screen.getByRole("button", { name: "Buscar encargado" }));
  await waitFor(() =>
    expect(mocks.listPage).toHaveBeenLastCalledWith({ page: 1, search: "Demo" })
  );
  await user.click(await screen.findByRole("button", { name: "Siguiente" }));
  await waitFor(() =>
    expect(mocks.listPage).toHaveBeenLastCalledWith({ page: 2, search: "Demo" })
  );
  expect(mocks.linkRecordGuardian).not.toHaveBeenCalled();
});

test("un error de busqueda permite reintentar sin confundirlo con cero resultados", async () => {
  mocks.listPage.mockRejectedValueOnce(new Error("Consulta no disponible"));
  const user = userEvent.setup();
  renderForm();
  await screen.findByText("Consulta no disponible");
  expect(
    screen.queryByText(/No se encontraron encargados/)
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Reintentar" }));
  await screen.findByRole("button", { name: "Elegir Responsable Demo" });
});

test("selecciona existente y usa un solo POST con estudiante UUID", async () => {
  const user = userEvent.setup();
  renderForm();
  await user.click(
    await screen.findByRole("button", { name: "Elegir Responsable Demo" })
  );
  await user.type(
    screen.getByLabelText(/Parentesco o responsabilidad/),
    "Tutor"
  );
  await user.click(screen.getByRole("button", { name: "Vincular encargado" }));
  await waitFor(() => expect(saved).toHaveBeenCalledOnce());
  expect(mocks.linkRecordGuardian).toHaveBeenCalledExactlyOnceWith(
    "student-1",
    { guardian_id: 7, relationship_label: "Tutor" }
  );
});

test("crea y vincula en una operacion, bloquea doble envio y conserva datos ante error", async () => {
  let reject;
  mocks.linkRecordGuardian.mockImplementationOnce(
    () =>
      new Promise((_resolve, fail) => {
        reject = fail;
      })
  );
  const user = userEvent.setup();
  renderForm();
  await user.click(
    await screen.findByRole("button", { name: "Crear encargado" })
  );
  for (const [label, value] of [
    [/^Nombres/, "Encargado"],
    [/^Apellidos/, "Nuevo"],
    [/^CUI/, "9876543210123"],
    [/^Fecha de nacimiento/, "1990-01-01"],
    [/^Nacionalidad/, "Guatemalteca"],
    [/^Teléfono/, "55500001"],
    [/^Dirección/, "Direccion demo"],
    [/^Departamento/, "Guatemala"],
    [/^Municipio/, "Guatemala"],
    [/^Parentesco/, "Tutor"],
  ])
    await user.type(screen.getByLabelText(label), value);
  await user.click(screen.getByLabelText(/^Sexo/));
  await user.click(screen.getByRole("option", { name: "Masculino" }));
  await user.dblClick(screen.getByRole("button", { name: "Crear y vincular" }));
  expect(mocks.linkRecordGuardian).toHaveBeenCalledOnce();
  expect(screen.getByRole("button", { name: "Cancelar" })).toBeDisabled();
  reject(new Error("No se pudo guardar"));
  await screen.findByText("No se pudo guardar");
  expect(screen.getByLabelText(/^Nombres/)).toHaveValue("Encargado");
  expect(saved).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Crear y vincular" }));
  await waitFor(() => expect(saved).toHaveBeenCalledOnce());
  expect(mocks.linkRecordGuardian).toHaveBeenLastCalledWith(
    "student-1",
    expect.objectContaining({
      person: expect.objectContaining({
        cui: "9876543210123",
        first_name: "Encargado",
        birth_date: "1990-01-01",
      }),
      relationship_label: "Tutor",
    })
  );
  // Completes the institutional form, rejects one write and retries under coverage.
}, 15000);

test("cancelar creacion vuelve a resultados sin guardar", async () => {
  const user = userEvent.setup();
  renderForm();
  await user.click(
    await screen.findByRole("button", { name: "Crear encargado" })
  );
  await user.click(screen.getByRole("button", { name: "Cancelar" }));
  await screen.findByRole("button", { name: "Elegir Responsable Demo" });
  expect(mocks.linkRecordGuardian).not.toHaveBeenCalled();
});
