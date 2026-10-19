import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

const accountsServiceMock = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  update: vi.fn(),
  provision: vi.fn(),
  candidates: vi.fn(),
  suggestUsername: vi.fn(),
  reissueActivation: vi.fn(),
  reactivate: vi.fn(),
  unlock: vi.fn(),
  disable: vi.fn(),
  closeSessions: vi.fn(),
  issuePasswordReset: vi.fn(),
  assignments: vi.fn(),
  assignRole: vi.fn(),
  revokeAssignment: vi.fn(),
  expiringAssignments: vi.fn(),
}));
vi.mock("@auth/accountsService.js", async (importOriginal) => ({
  ...(await importOriginal()),
  accountsService: accountsServiceMock,
}));
const rolesServiceMock = vi.hoisted(() => ({
  listAll: vi.fn(),
  listPage: vi.fn(),
  permissions: vi.fn(),
  scopeOptions: vi.fn(),
}));
vi.mock("@auth/rolesService.js", async (importOriginal) => ({
  ...(await importOriginal()),
  rolesService: rolesServiceMock,
}));

import { AccountDetailPage } from "@auth/AccountDetailPage.jsx";
import { AccountsPage } from "@auth/AccountsPage.jsx";
import { GrantAccessWindow } from "@auth/GrantAccessWindow.jsx";

import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";

const ADMIN = sessionUser([
  "account.create",
  "account.activate",
  "account.disable",
  "role.assign",
]);

function account(overrides = {}) {
  return {
    public_id: "acc-1",
    username: "ana.lopez",
    email: "ana@example.test",
    status: "active",
    status_display: "Activa",
    is_active: true,
    person_name: "Ana López",
    person: { public_id: "per-1", full_name: "Ana López", is_teacher: false },
    roles: [{ public_id: "r-1", name: "Secretaría", ends_at: null }],
    last_login: "2026-10-01T15:00:00Z",
    locked_until: null,
    is_locked: false,
    ...overrides,
  };
}

function page(rows) {
  return { count: rows.length, next: null, previous: null, results: rows };
}

beforeEach(() => {
  Object.values(accountsServiceMock).forEach((fn) => fn.mockReset());
  Object.values(rolesServiceMock).forEach((fn) => fn.mockReset());
  accountsServiceMock.list.mockResolvedValue(
    page([
      account(),
      account({
        public_id: "acc-2",
        username: "luis",
        email: "luis@example.test",
        person_name: "Luis Pérez",
        status: "disabled",
        status_display: "Desactivada",
        roles: [],
      }),
      account({
        public_id: "acc-3",
        username: "bloq",
        email: "bea@example.test",
        person_name: "Bea Bloq",
        is_locked: true,
        locked_until: "2026-10-17T20:00:00Z",
      }),
    ])
  );
  accountsServiceMock.expiringAssignments.mockResolvedValue(page([]));
  rolesServiceMock.listAll.mockResolvedValue([
    { public_id: "r-1", name: "Secretaría", permissions: [] },
  ]);
});

describe("AccountsPage (U4, U9, U3, RA5)", () => {
  test("lista correo, roles, estado traducido, bloqueo y ultimo acceso", async () => {
    renderWithSession(<AccountsPage />, { user: ADMIN, route: "/app/cuentas" });

    const row = (await screen.findByText("ana@example.test")).closest("tr");
    expect(within(row).getByText("Secretaría")).toBeInTheDocument();
    expect(within(row).getByText("Activa")).toBeInTheDocument();
    expect(screen.getByText("Desactivada")).toBeInTheDocument();
    expect(screen.getByText(/Bloqueada hasta/)).toBeInTheDocument();
    expect(
      screen.getByRole("columnheader", { name: "Último acceso" })
    ).toBeInTheDocument();
    expect(accountsServiceMock.list).toHaveBeenCalledWith({
      page: 1,
      page_size: 25,
    });
  });

  test("el filtro de estado se envia al servidor", async () => {
    const user = userEvent.setup();
    renderWithSession(<AccountsPage />, { user: ADMIN, route: "/app/cuentas" });
    await screen.findByText("ana@example.test");

    await user.click(screen.getByLabelText("Estado"));
    await user.click(
      within(await screen.findByRole("listbox")).getByRole("option", {
        name: "Pendiente",
      })
    );

    await waitFor(() =>
      expect(accountsServiceMock.list).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 25,
        status: "pending",
      })
    );
  });

  test("las acciones van en un menu y dependen del estado", async () => {
    const user = userEvent.setup();
    renderWithSession(<AccountsPage />, { user: ADMIN, route: "/app/cuentas" });
    await screen.findByText("ana@example.test");

    await user.click(screen.getByRole("button", { name: "Acciones de luis" }));
    const menu = await screen.findByRole("menu");
    expect(within(menu).getByText("Reactivar")).toBeInTheDocument();
    expect(within(menu).queryByText("Desactivar")).not.toBeInTheDocument();
    expect(within(menu).queryByText("Desbloquear")).not.toBeInTheDocument();
  });

  test("restablecer acceso entrega el enlace completo con su vencimiento", async () => {
    const user = userEvent.setup();
    accountsServiceMock.issuePasswordReset.mockResolvedValue({
      token: "tok-123",
      expires_at: "2026-10-17T20:30:00Z",
    });
    renderWithSession(<AccountsPage />, { user: ADMIN, route: "/app/cuentas" });
    await screen.findByText("ana@example.test");

    await user.click(
      screen.getByRole("button", { name: "Acciones de ana.lopez" })
    );
    await user.click(await screen.findByText("Restablecer acceso"));

    expect(
      await screen.findByText(
        `${window.location.origin}/restablecer?token=tok-123`
      )
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copiar" })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Imprimir instrucciones" })
    ).toBeInTheDocument();
  });

  test("sin permisos de escritura no se ofrecen acciones ni 'Dar acceso'", async () => {
    renderWithSession(<AccountsPage />, {
      user: sessionUser(["account.disable"]),
      route: "/app/cuentas",
    });
    await screen.findByText("ana@example.test");

    expect(
      screen.queryByRole("button", { name: "Dar acceso al sistema" })
    ).not.toBeInTheDocument();
  });

  test("avisa las asignaciones de rol por vencer (RA5)", async () => {
    accountsServiceMock.expiringAssignments.mockResolvedValue(
      page([
        {
          assignment: "as-1",
          account: "acc-1",
          username: "ana.lopez",
          person_name: "Ana López",
          role_name: "Docente",
          ends_at: "2026-10-25T00:00:00Z",
          status: "expiring",
        },
      ])
    );
    renderWithSession(<AccountsPage />, { user: ADMIN, route: "/app/cuentas" });

    expect(
      await screen.findByText(/1 asignación\(es\) de rol vencen/)
    ).toBeInTheDocument();
  });
});

describe("GrantAccessWindow (U1, D9)", () => {
  test("busca a la persona, sugiere el usuario y muestra el codigo una vez", async () => {
    const user = userEvent.setup();
    accountsServiceMock.candidates.mockResolvedValue(
      page([
        {
          public_id: "per-9",
          full_name: "Marta Xicará",
          email: "marta@example.test",
          cui_hint: "…0101",
          profiles: ["teacher"],
        },
      ])
    );
    accountsServiceMock.suggestUsername.mockResolvedValue({
      username: "marta.xicara",
    });
    accountsServiceMock.provision.mockResolvedValue({
      public_id: "acc-9",
      username: "marta.xicara",
      activation_code: "48213977",
      activation_expires_at: "2026-10-18T10:00:00Z",
    });
    renderWithSession(<GrantAccessWindow onClose={vi.fn()} open />, {
      user: ADMIN,
    });

    // D9: no se ofrecen cuentas de encargado.
    expect(screen.queryByText(/encargado/i)).not.toBeInTheDocument();
    await user.type(screen.getByLabelText(/Persona/), "Marta");
    await user.click(
      await screen.findByText(/Marta Xicará · CUI …0101 · Docente/)
    );

    await waitFor(() =>
      expect(screen.getByLabelText(/Usuario/)).toHaveValue("marta.xicara")
    );
    expect(screen.getByLabelText(/Correo/)).toHaveValue("marta@example.test");
    await user.click(screen.getByRole("button", { name: "Crear cuenta" }));

    expect(accountsServiceMock.provision).toHaveBeenCalledWith({
      personPublicId: "per-9",
      username: "marta.xicara",
      email: "marta@example.test",
    });
    expect(await screen.findByText("48213977")).toBeInTheDocument();
    expect(screen.getByText(/Se muestra una sola vez/)).toBeInTheDocument();
  });
});

describe("AccountDetailPage (U5, D8, RA2)", () => {
  function renderDetail(detail) {
    accountsServiceMock.get.mockResolvedValue({
      ...account(),
      date_joined: "2026-01-01T12:00:00Z",
      failed_login_attempts: 0,
      sessions: [
        {
          last_activity_at: "2026-10-17T15:00:00Z",
          expires_at: "2026-10-17T16:00:00Z",
          is_current: false,
        },
      ],
      recent_activity: [
        {
          action: "identity.login.succeeded",
          created_at: "2026-10-17T15:00:00Z",
          ip_address: "10.0.0.1",
          actor_label: "ana.lopez",
          result: "success",
        },
      ],
      activation_expires_at: null,
      ...detail,
    });
    accountsServiceMock.assignments.mockResolvedValue(
      page([
        {
          public_id: "as-1",
          role_name: "Secretaría",
          starts_at: "2026-01-01T00:00:00Z",
          ends_at: null,
          status: "active",
          status_display: "Vigente",
          scopes: [
            {
              public_id: "sg-1",
              dimensions: [
                { dimension: "module", label: "Expedientes de estudiantes" },
              ],
            },
          ],
        },
      ])
    );
    return renderWithSession(
      <Routes>
        <Route element={<AccountDetailPage />} path="/app/cuentas/:accountId" />
      </Routes>,
      { user: ADMIN, route: "/app/cuentas/acc-1" }
    );
  }

  test("muestra roles con alcance, sesiones e historial de accesos", async () => {
    renderDetail();

    expect(
      await screen.findByText("Expedientes de estudiantes")
    ).toBeInTheDocument();
    expect(screen.getByText("Inicio de sesión")).toBeInTheDocument();
    expect(screen.getByText("10.0.0.1")).toBeInTheDocument();
    expect(screen.getByText("Vigente")).toBeInTheDocument();
    expect(accountsServiceMock.get).toHaveBeenCalledWith("acc-1");
  });

  test("reactivar pide motivo, advierte que los roles no vuelven y entrega el codigo nuevo", async () => {
    const user = userEvent.setup();
    accountsServiceMock.reactivate.mockResolvedValue({
      account: account({ status: "pending", status_display: "Pendiente" }),
      activation_code: "99887766",
      activation_expires_at: "2026-10-18T10:00:00Z",
    });
    renderDetail({ status: "disabled", status_display: "Desactivada" });

    await user.click(
      await screen.findByRole("button", { name: "Acciones de ana.lopez" })
    );
    await user.click(
      within(await screen.findByRole("menu")).getByText("Reactivar")
    );
    expect(
      screen.getByText(/Los roles revocados no vuelven solos/)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Reactivar" }));
    expect(await screen.findByText(/Escriba el motivo/)).toBeInTheDocument();
    expect(accountsServiceMock.reactivate).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText(/Motivo/), "Desactivada por error");
    await user.click(screen.getByRole("button", { name: "Reactivar" }));

    expect(accountsServiceMock.reactivate).toHaveBeenCalledWith(
      "acc-1",
      "Desactivada por error"
    );
    expect(await screen.findByText("99887766")).toBeInTheDocument();
  });

  test("desbloquear una cuenta bloqueada pide motivo", async () => {
    const user = userEvent.setup();
    accountsServiceMock.unlock.mockResolvedValue(account());
    renderDetail({ is_locked: true, locked_until: "2026-10-17T20:00:00Z" });

    await user.click(
      await screen.findByRole("button", { name: "Acciones de ana.lopez" })
    );
    await user.click(await screen.findByText("Desbloquear"));
    await user.type(
      screen.getByLabelText(/Motivo/),
      "Verificada en ventanilla"
    );
    await user.click(screen.getByRole("button", { name: "Desbloquear" }));

    await waitFor(() =>
      expect(accountsServiceMock.unlock).toHaveBeenCalledWith(
        "acc-1",
        "Verificada en ventanilla"
      )
    );
  });

  test("revocar una asignacion confirma y la conserva en el historial", async () => {
    const user = userEvent.setup();
    accountsServiceMock.revokeAssignment.mockResolvedValue({});
    renderDetail();

    await user.click(await screen.findByRole("button", { name: "Revocar" }));
    expect(screen.getByText(/queda en el historial/)).toBeInTheDocument();
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "Revocar",
      })
    );

    expect(accountsServiceMock.revokeAssignment).toHaveBeenCalledWith("as-1");
  });
});
