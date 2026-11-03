import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

const cyclesServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  activate: vi.fn(),
  close: vi.fn(),
  clone: vi.fn(),
  reopen: vi.fn(),
  revertToDraft: vi.fn(),
  readiness: vi.fn(),
  defaults: vi.fn(),
}));

vi.mock("@cycles/cyclesService.js", async (importOriginal) => {
  const original = await importOriginal();
  return { ...original, cyclesService: cyclesServiceMock };
});

import { CyclesPage } from "@cycles/CyclesPage.jsx";
import { paginated } from "./fixtures/academics.js";
import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";

const ADMIN = sessionUser([
  "scope.assign",
  "academic_cycle.reopen",
  "academic_cycle.revert",
]);

const cycle = (overrides) => ({
  public_id: "c-2026",
  year: 2026,
  name: "Ciclo 2026",
  starts_on: "2026-01-15",
  ends_on: "2026-10-30",
  description: "",
  status: "active",
  ...overrides,
});

const ACTIVE = cycle();
const DRAFT = cycle({
  public_id: "c-2027",
  year: 2027,
  name: "Ciclo 2027",
  starts_on: "2027-01-15",
  ends_on: "2027-10-29",
  status: "draft",
});
const CLOSED = cycle({
  public_id: "c-2025",
  year: 2025,
  name: "Ciclo 2025",
  status: "closed",
});

const readiness = (overrides = {}) => ({
  activation: { ready: false, gaps: [] },
  revert: { allowed: true, blockers: [] },
  close: { ready: true, gaps: [] },
  active_cycle: null,
  ...overrides,
});

function renderPage(user = ADMIN) {
  return renderWithSession(
    <Routes>
      <Route element={<CyclesPage />} path="/app/ciclos" />
      <Route element={<p>Detalle abierto</p>} path="/app/ciclos/:cycleId" />
    </Routes>,
    { user, route: "/app/ciclos" }
  );
}

async function openMenu(user, name) {
  await user.click(
    await screen.findByRole("button", { name: `Acciones de ${name}` })
  );
  return screen.findByRole("menu");
}

describe("listado de ciclos escolares", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    cyclesServiceMock.list.mockResolvedValue(
      paginated([DRAFT, ACTIVE, CLOSED])
    );
    cyclesServiceMock.readiness.mockResolvedValue(readiness());
    cyclesServiceMock.defaults.mockImplementation(async (year) => ({
      year: Number(year),
      name: `Ciclo ${year}`,
      starts_on: `${year}-01-15`,
      ends_on: `${year}-10-29`,
    }));
  });

  test("lista con columnas con tilde y un subtítulo que no promete cerrar el anterior", async () => {
    renderPage();

    expect(await screen.findByText("Ciclo 2026")).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Año" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Descripción" })
    ).toBeInTheDocument();
    expect(screen.getByText("Borrador")).toBeInTheDocument();
    expect(screen.queryByText(/cierra el anterior/)).not.toBeInTheDocument();
    expect(cyclesServiceMock.list).toHaveBeenCalledWith({
      page: 1,
      page_size: 25,
    });
  });

  test("con otro ciclo activo, Activar queda deshabilitado y dice cuál cerrar (D1)", async () => {
    const user = userEvent.setup();
    renderPage();

    const alert = await screen.findByText(/El ciclo activo es «Ciclo 2026»/);
    expect(
      within(alert.closest('[role="alert"]') ?? alert.parentElement).getByRole(
        "link",
        { name: "Ver «Ciclo 2026»" }
      )
    ).toHaveAttribute("href", "/app/ciclos/c-2026");

    const menu = await openMenu(user, "Ciclo 2027");
    const activate = within(menu).getByRole("menuitem", { name: /Activar/ });
    expect(activate).toHaveAttribute("aria-disabled", "true");
    expect(activate).toHaveTextContent("Cierre primero el ciclo «Ciclo 2026».");
  });

  test("activar confirma con un texto veraz y llama al backend", async () => {
    const user = userEvent.setup();
    cyclesServiceMock.list.mockResolvedValue(paginated([DRAFT, CLOSED]));
    cyclesServiceMock.activate.mockResolvedValue({
      ...DRAFT,
      status: "active",
    });
    renderPage();

    const menu = await openMenu(user, "Ciclo 2027");
    await user.click(within(menu).getByRole("menuitem", { name: /Activar/ }));

    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent("pasará a ser el ciclo vigente");
    expect(dialog).not.toHaveTextContent(/anterior queda cerrado/);
    expect(cyclesServiceMock.activate).not.toHaveBeenCalled();

    await user.click(
      within(dialog).getByRole("button", { name: "Sí, activar" })
    );
    await waitFor(() =>
      expect(cyclesServiceMock.activate).toHaveBeenCalledWith("c-2027")
    );
  });

  test("muestra el motivo del backend si activar se rechaza", async () => {
    const user = userEvent.setup();
    cyclesServiceMock.list.mockResolvedValue(paginated([DRAFT]));
    cyclesServiceMock.activate.mockRejectedValue(
      new Error(
        "La estructura del ciclo escolar está incompleta: faltan secciones."
      )
    );
    renderPage();

    const menu = await openMenu(user, "Ciclo 2027");
    await user.click(within(menu).getByRole("menuitem", { name: /Activar/ }));
    await user.click(screen.getByRole("button", { name: "Sí, activar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "faltan secciones"
    );
  });

  test("clonar se deshabilita en borradores y explica por qué (D2)", async () => {
    const user = userEvent.setup();
    renderPage();

    const menu = await openMenu(user, "Ciclo 2027");
    const clone = within(menu).getByRole("menuitem", {
      name: /Clonar estructura/,
    });
    expect(clone).toHaveAttribute("aria-disabled", "true");
    expect(clone).toHaveTextContent("Un borrador no se clona");
  });

  test("clona un ciclo activo con sus asignaciones y abre el ciclo nuevo", async () => {
    const user = userEvent.setup();
    cyclesServiceMock.clone.mockResolvedValue({ ...DRAFT, public_id: "nuevo" });
    renderPage();

    const menu = await openMenu(user, "Ciclo 2026");
    await user.click(
      within(menu).getByRole("menuitem", { name: /Clonar estructura/ })
    );
    await screen.findByDisplayValue("Ciclo 2027");
    await user.click(
      screen.getByLabelText(/Copiar también las asignaciones docentes/)
    );
    await user.click(screen.getByRole("button", { name: "Clonar estructura" }));

    await waitFor(() =>
      expect(cyclesServiceMock.clone).toHaveBeenCalledWith(
        "c-2026",
        expect.objectContaining({ include_teaching_assignments: true })
      )
    );
    expect(await screen.findByText("Detalle abierto")).toBeInTheDocument();
  });

  test("edita un borrador conservando lo guardado (C3)", async () => {
    const user = userEvent.setup();
    cyclesServiceMock.list.mockResolvedValue(
      paginated([{ ...DRAFT, name: "Ciclo 2027 piloto", description: "Plan" }])
    );
    cyclesServiceMock.update.mockResolvedValue(DRAFT);
    renderPage();

    const menu = await openMenu(user, "Ciclo 2027 piloto");
    await user.click(within(menu).getByRole("menuitem", { name: "Editar" }));

    expect(
      await screen.findByDisplayValue("Ciclo 2027 piloto")
    ).toBeInTheDocument();
    // Al abrir no se recalculan nombre ni fechas: se respeta lo guardado.
    expect(cyclesServiceMock.defaults).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() =>
      expect(cyclesServiceMock.update).toHaveBeenCalledWith("c-2027", {
        year: 2027,
        name: "Ciclo 2027 piloto",
        starts_on: "2027-01-15",
        ends_on: "2027-10-29",
        description: "Plan",
      })
    );
  });

  test("volver a borrador se deshabilita con los bloqueos del ciclo (D6)", async () => {
    const user = userEvent.setup();
    cyclesServiceMock.readiness.mockResolvedValue(
      readiness({
        revert: {
          allowed: false,
          blockers: [
            {
              code: "enrolments",
              count: 312,
              message: "Tiene 312 matrículas.",
            },
          ],
        },
      })
    );
    renderPage();

    await waitFor(() =>
      expect(cyclesServiceMock.readiness).toHaveBeenCalledWith("c-2026")
    );
    const menu = await openMenu(user, "Ciclo 2026");
    const revert = await within(menu).findByRole("menuitem", {
      name: /Volver a borrador/,
    });
    await waitFor(() =>
      expect(revert).toHaveAttribute("aria-disabled", "true")
    );
    expect(revert).toHaveTextContent("Tiene 312 matrículas.");
  });

  test("volver a borrador pide motivo y llama al backend", async () => {
    const user = userEvent.setup();
    cyclesServiceMock.revertToDraft.mockResolvedValue({
      ...ACTIVE,
      status: "draft",
    });
    renderPage();

    const menu = await openMenu(user, "Ciclo 2026");
    await user.click(
      within(menu).getByRole("menuitem", { name: /Volver a borrador/ })
    );
    const dialog = await screen.findByRole("dialog");
    await user.click(
      within(dialog).getByRole("button", { name: "Volver a borrador" })
    );
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(
      "Escriba el motivo"
    );

    await user.type(
      within(dialog).getByLabelText(/Motivo/),
      "Activado por error"
    );
    await user.click(
      within(dialog).getByRole("button", { name: "Volver a borrador" })
    );
    await waitFor(() =>
      expect(cyclesServiceMock.revertToDraft).toHaveBeenCalledWith(
        "c-2026",
        "Activado por error"
      )
    );
  });

  test("reabre un ciclo cerrado con motivo (C6)", async () => {
    const user = userEvent.setup();
    cyclesServiceMock.reopen.mockResolvedValue({ ...CLOSED, status: "active" });
    renderPage();

    const menu = await openMenu(user, "Ciclo 2025");
    await user.click(within(menu).getByRole("menuitem", { name: "Reabrir" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(
      within(dialog).getByLabelText(/Motivo/),
      "Corrección de notas"
    );
    await user.click(
      within(dialog).getByRole("button", { name: "Reabrir ciclo" })
    );

    await waitFor(() =>
      expect(cyclesServiceMock.reopen).toHaveBeenCalledWith(
        "c-2025",
        "Corrección de notas"
      )
    );
  });

  test("cierra el ciclo activo tras confirmar y muestra el rechazo del backend", async () => {
    const user = userEvent.setup();
    cyclesServiceMock.close.mockRejectedValue(
      new Error("La unidad de evaluación 'U1' sigue abierta.")
    );
    renderPage();

    const menu = await openMenu(user, "Ciclo 2026");
    await user.click(
      within(menu).getByRole("menuitem", { name: "Cerrar ciclo" })
    );
    await user.click(screen.getByRole("button", { name: "Sí, cerrar ciclo" }));

    await waitFor(() =>
      expect(cyclesServiceMock.close).toHaveBeenCalledWith("c-2026")
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("sigue abierta");
  });

  test("sin permisos solo se consulta: sin alta ni acciones de ciclo de vida", async () => {
    const user = userEvent.setup();
    renderPage(sessionUser([]));

    await screen.findByText("Ciclo 2026");
    expect(
      screen.queryByRole("button", { name: "Nuevo ciclo" })
    ).not.toBeInTheDocument();
    const menu = await openMenu(user, "Ciclo 2026");
    expect(within(menu).getAllByRole("menuitem")).toHaveLength(1);
    expect(
      within(menu).getByRole("menuitem", { name: "Ver detalle" })
    ).toBeInTheDocument();
  });

  test("la fila abre el detalle del ciclo", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByText("Ciclo 2025"));
    expect(await screen.findByText("Detalle abierto")).toBeInTheDocument();
  });
});

describe("formulario de ciclo nuevo", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    cyclesServiceMock.list.mockResolvedValue(paginated([ACTIVE]));
    cyclesServiceMock.readiness.mockResolvedValue(readiness());
    cyclesServiceMock.create.mockResolvedValue(DRAFT);
    cyclesServiceMock.defaults.mockImplementation(async (year) => ({
      year: Number(year),
      name: `Ciclo ${year}`,
      starts_on: `${year}-01-15`,
      ends_on: `${year}-10-29`,
    }));
  });

  test("el ciclo se define por su año: nombre y vigencia se derivan", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(
      await screen.findByRole("button", { name: "Nuevo ciclo" })
    );
    expect(await screen.findByDisplayValue("Ciclo 2027")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2027-01-15")).toBeInTheDocument();
    expect(
      screen.getByRole("combobox", { name: /Año del ciclo/ })
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Crear ciclo" }));
    await waitFor(() =>
      expect(cyclesServiceMock.create).toHaveBeenCalledWith({
        year: 2027,
        name: "Ciclo 2027",
        starts_on: "2027-01-15",
        ends_on: "2027-10-29",
        description: "",
      })
    );
    // El ciclo nuevo abre su tablero de preparación.
    expect(await screen.findByText("Detalle abierto")).toBeInTheDocument();
  });

  test("cambiar el año recalcula nombre y vigencia", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(
      await screen.findByRole("button", { name: "Nuevo ciclo" })
    );
    await screen.findByDisplayValue("Ciclo 2027");
    await user.click(screen.getByLabelText(/^Año del ciclo/));
    await user.click(await screen.findByRole("option", { name: "2029" }));

    expect(await screen.findByDisplayValue("Ciclo 2029")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2029-01-15")).toBeInTheDocument();
  });
});
