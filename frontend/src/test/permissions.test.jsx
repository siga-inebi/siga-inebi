import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router-dom";
import { describe, expect, test, vi } from "vitest";

import { canViewModule, NAV_GROUPS, visibleGroups } from "@app/navigation.js";
import { Can } from "@auth/Can.jsx";
import {
  canAccessModule,
  hasAnyPermission,
  hasPermission,
  MODULE_PERMISSIONS,
} from "@auth/permissions.js";

import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";

describe("permisos efectivos en la interfaz (ux-ui 1.4)", () => {
  test("sin sesion no hay permisos; con sesion se consultan los efectivos", () => {
    expect(hasPermission(null, "audit.read")).toBe(false);
    const user = sessionUser(["audit.read"]);
    expect(hasPermission(user, "audit.read")).toBe(true);
    expect(hasPermission(user, "platform.monitor")).toBe(false);
    expect(hasAnyPermission(user, ["platform.monitor", "audit.read"])).toBe(
      true
    );
    expect(hasAnyPermission(user, [])).toBe(true);
  });

  test("un superusuario tiene todos los permisos", () => {
    const user = sessionUser([], { is_superuser: true });
    expect(hasPermission(user, "platform.monitor")).toBe(true);
  });

  test("cada modulo con permiso atomico se oculta sin el; los demas no", () => {
    const user = sessionUser([]);
    const items = Object.fromEntries(
      NAV_GROUPS.flatMap((group) => group.items).map((item) => [item.key, item])
    );

    expect(canViewModule(user, items.docentes)).toBe(true);
    expect(canViewModule(user, items.ciclos)).toBe(true);
    expect(canViewModule(user, items.alumnos)).toBe(false);
    expect(canViewModule(user, items.cuentas)).toBe(false);
    expect(canViewModule(null, items.docentes)).toBe(false);
    expect(
      canAccessModule(sessionUser(["account.disable"]), {
        permissions: MODULE_PERMISSIONS.cuentas,
      })
    ).toBe(true);
  });

  test("el grupo Administracion solo aparece con alguno de sus permisos (2.17.6)", () => {
    const without = visibleGroups(sessionUser([])).map((group) => group.key);
    const withAudit = visibleGroups(sessionUser(["audit.read"]));

    expect(without).not.toContain("administracion");
    expect(
      withAudit
        .find((group) => group.key === "administracion")
        .items.map((item) => item.key)
    ).toEqual(["auditoria"]);
  });

  test("<Can> muestra la accion solo con el permiso", () => {
    renderWithSession(
      <>
        <Can permission="account.create">
          <button type="button">Dar acceso</button>
        </Can>
        <Can fallback={<span>Sin permiso</span>} permission="role.assign">
          <button type="button">Asignar rol</button>
        </Can>
      </>,
      { user: sessionUser(["account.create"]) }
    );

    expect(
      screen.getByRole("button", { name: "Dar acceso" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Asignar rol" })
    ).not.toBeInTheDocument();
    expect(screen.getByText("Sin permiso")).toBeInTheDocument();
  });
});

const authServiceMock = vi.hoisted(() => ({
  me: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  logoutAll: vi.fn(),
  csrf: vi.fn(),
}));
vi.mock("@auth/authService.js", () => ({ authService: authServiceMock }));

describe("rutas protegidas por permiso", () => {
  test("una ruta sin permiso explica 'sin acceso' en vez de montar la pantalla", async () => {
    const { App } = await import("../app/App.jsx");
    const { apiClient } = await import("@shared/api/apiClient.js");
    vi.spyOn(apiClient, "get").mockResolvedValue({ results: [], count: 0 });
    authServiceMock.me.mockResolvedValue({
      authenticated: true,
      user: sessionUser(["student.view_basic"]),
    });
    const { renderWithRouter } = await import("./helpers/renderWithRouter.jsx");

    renderWithRouter(
      <Routes>
        <Route element={<App />} path="*" />
      </Routes>,
      { route: "/app/plataforma" }
    );

    expect(
      await screen.findByRole("heading", { name: "Sin acceso" })
    ).toBeInTheDocument();
    expect(screen.getByText(/«Plataforma»/)).toBeInTheDocument();
  });
});
