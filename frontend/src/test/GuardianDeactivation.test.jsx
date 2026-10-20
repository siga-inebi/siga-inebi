import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { GuardiansPage } from "@guardians/GuardiansPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const service = vi.hoisted(() => ({
  list: vi.fn(),
  listPage: vi.fn(),
  deactivate: vi.fn(),
}));
vi.mock("@guardians/guardiansService.js", () => ({
  guardiansService: service,
}));

const guardian = {
  id: 27,
  is_active: true,
  actions: { deactivate: true },
  person: {
    first_name: "Encargado",
    last_name: "Sintetico",
    email: "",
    phone_number: "",
  },
};

async function openDetail(user) {
  await user.click(
    await screen.findByRole("button", { name: /Ver detalle de Encargado/ })
  );
  return screen.getByRole("dialog");
}

async function openConfirmation(user) {
  const detail = await openDetail(user);
  await user.click(
    within(detail).getByRole("button", { name: "Desactivar encargado" })
  );
  return screen.findByRole("dialog", { name: "Desactivar encargado" });
}

describe("G3 desactivación de encargados", () => {
  beforeEach(() => {
    service.list.mockReset().mockResolvedValue([guardian]);
    // El listado pide páginas al servidor; `list` sigue siendo la fuente de
    // las filas para contar cada recarga.
    service.listPage.mockReset().mockImplementation(async () => {
      const results = await service.list();
      return { results, count: results.length, next: null, previous: null };
    });
    service.deactivate.mockReset().mockResolvedValue(undefined);
  });

  test.each([
    { actions: undefined },
    { actions: { deactivate: false } },
    { is_active: false },
  ])(
    "oculta la acción sin capacidad o con perfil desactivado: %j",
    async (changes) => {
      service.list.mockResolvedValue([{ ...guardian, ...changes }]);
      const user = userEvent.setup();
      renderWithRouter(<GuardiansPage />);
      const detail = await openDetail(user);
      expect(
        within(detail).queryByRole("button", { name: "Desactivar encargado" })
      ).not.toBeInTheDocument();
      expect(service.deactivate).not.toHaveBeenCalled();
    }
  );

  test("confirmación explica el acceso derivado y cancelar restaura el detalle sin escribir", async () => {
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);
    const dialog = await openConfirmation(user);
    expect(
      within(dialog).getByText(
        /Dejará de obtener acceso a estudiantes por esos vínculos/
      )
    ).toBeInTheDocument();
    expect(screen.getAllByRole("dialog")).toHaveLength(1);
    await user.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    expect(
      await screen.findByRole("dialog", { name: "Encargado Sintetico" })
    ).toBeInTheDocument();
    expect(service.deactivate).not.toHaveBeenCalled();
  });

  test("confirma una vez, cierra y consulta de nuevo el listado", async () => {
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);
    const dialog = await openConfirmation(user);
    service.list.mockResolvedValue([]);
    await user.click(
      within(dialog).getByRole("button", { name: "Desactivar encargado" })
    );
    expect(
      await screen.findByText(
        "Encargado desactivado. El historial se conserva."
      )
    ).toBeInTheDocument();
    await waitFor(() => expect(service.list).toHaveBeenCalledTimes(2));
    expect(service.deactivate).toHaveBeenCalledExactlyOnceWith(27);
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    );
    expect(
      await screen.findByText("No hay encargados registrados.")
    ).toBeInTheDocument();
  });

  test("un rechazo conserva la confirmación y permite reintentar", async () => {
    service.deactivate.mockRejectedValueOnce(
      new Error("El permiso ya no está vigente.")
    );
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);
    const dialog = await openConfirmation(user);
    await user.click(
      within(dialog).getByRole("button", { name: "Desactivar encargado" })
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "El permiso ya no está vigente."
    );
    expect(service.list).toHaveBeenCalledTimes(1);
    await user.click(
      within(dialog).getByRole("button", { name: "Desactivar encargado" })
    );
    await waitFor(() => expect(service.deactivate).toHaveBeenCalledTimes(2));
    expect(
      await screen.findByText(
        "Encargado desactivado. El historial se conserva."
      )
    ).toBeInTheDocument();
  });

  test("bloquea doble envío, Escape y cancelar mientras procesa", async () => {
    let resolve;
    service.deactivate.mockImplementation(
      () =>
        new Promise((done) => {
          resolve = done;
        })
    );
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);
    const dialog = await openConfirmation(user);
    await user.dblClick(
      within(dialog).getByRole("button", { name: "Desactivar encargado" })
    );
    expect(
      within(dialog).getByRole("button", { name: "Cancelar" })
    ).toBeDisabled();
    expect(
      within(dialog).getByRole("button", { name: "Desactivar encargado" })
    ).toBeDisabled();
    await user.keyboard("{Escape}");
    expect(dialog).toBeInTheDocument();
    expect(service.deactivate).toHaveBeenCalledTimes(1);
    resolve();
    expect(
      await screen.findByText(
        "Encargado desactivado. El historial se conserva."
      )
    ).toBeInTheDocument();
  });

  test("un fallo de recarga no vuelve a ofrecer una escritura ya confirmada", async () => {
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);
    const dialog = await openConfirmation(user);
    service.list.mockRejectedValue(new Error("No se pudo recargar."));
    await user.click(
      within(dialog).getByRole("button", { name: "Desactivar encargado" })
    );
    expect(await screen.findByText("No se pudo recargar.")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    );
    expect(service.deactivate).toHaveBeenCalledTimes(1);
  });
});
