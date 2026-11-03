import { vi } from "vitest";

import { AuthContext } from "@auth/context.js";

import { renderWithRouter } from "./renderWithRouter.jsx";

/**
 * Renderiza con una sesion ya resuelta, sin pasar por `/auth/me/`.
 *
 * Las pantallas de administracion deciden que mostrar con los permisos
 * efectivos de la sesion (`user.permissions`); este helper deja fijar esos
 * permisos por prueba.
 */
export function renderWithSession(ui, { user, route = "/", ...auth } = {}) {
  const value = {
    user,
    loading: false,
    isAuthenticated: Boolean(user),
    login: vi.fn(),
    logout: vi.fn(),
    logoutAll: vi.fn(),
    refreshUser: vi.fn(),
    sessionNotice: null,
    clearSessionNotice: vi.fn(),
    ...auth,
  };
  return renderWithRouter(
    <AuthContext.Provider value={value}>{ui}</AuthContext.Provider>,
    { route }
  );
}

export function sessionUser(permissions = [], extra = {}) {
  return {
    public_id: "00000000-0000-4000-8000-0000000000aa",
    username: "admin",
    email: "admin@example.test",
    status: "active",
    status_display: "Activa",
    is_superuser: false,
    permissions,
    roles: [],
    session_idle_timeout_minutes: 30,
    person: { public_id: "p-1", first_name: "Demo", last_name: "Admin" },
    ...extra,
  };
}
