import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { App } from "../app/App.jsx";
import { AppErrorBoundary } from "@ui/feedback/AppErrorBoundary.jsx";
import { AuthProvider } from "@auth/AuthProvider.jsx";
import { AppShell } from "@layout/AppShell.jsx";
import { PublicShell } from "@layout/PublicShell.jsx";
import { LoginPage } from "@auth/LoginPage.jsx";
import { NotFoundPage } from "@ui/feedback/NotFoundPage.jsx";
import { apiClient } from "@shared/api/apiClient.js";
import { authenticatedSession, anonymousSession } from "./fixtures/auth.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const authServiceMock = vi.hoisted(() => ({
  me: vi.fn().mockResolvedValue({ authenticated: false, user: null }),
  login: vi.fn(),
  logout: vi.fn(),
  logoutAll: vi.fn(),
  csrf: vi.fn(),
}));

vi.mock("@auth/authService.js", () => ({
  authService: authServiceMock,
}));

describe("app shell", () => {
  beforeEach(() => {
    authServiceMock.me.mockResolvedValue(anonymousSession);
    authServiceMock.csrf.mockResolvedValue(undefined);
    authServiceMock.login.mockResolvedValue(authenticatedSession.user);
    authServiceMock.logout.mockResolvedValue(undefined);
    authServiceMock.logoutAll.mockResolvedValue(undefined);
  });

  test("redirects the public root directly to login", async () => {
    authServiceMock.me.mockResolvedValueOnce(anonymousSession);
    renderWithRouter(<App />);

    expect(
      await screen.findByRole("heading", { name: /Iniciar sesión/i })
    ).toBeInTheDocument();
  });

  test("redirects the authenticated root to the operational dashboard", async () => {
    authServiceMock.me.mockResolvedValueOnce(authenticatedSession);
    const apiSpy = vi
      .spyOn(apiClient, "get")
      .mockResolvedValue({ count: 0, results: [] });

    renderWithRouter(<App />);

    expect(
      await screen.findByRole("heading", { name: /Buen día, Demo/i })
    ).toBeInTheDocument();
    apiSpy.mockRestore();
  });

  test("public shell offers login and hides the module navigation", async () => {
    renderWithRouter(
      <AuthProvider>
        <PublicShell>
          <div>Contenido</div>
        </PublicShell>
      </AuthProvider>
    );

    expect(await screen.findByText("SIGA-INEBI")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Iniciar sesión/i })
    ).toBeInTheDocument();
    // Sin sesion no hay modulos que mostrar, asi que no debe haber grupos de nav.
    expect(
      screen.queryByRole("navigation", { name: "Comunidad educativa" })
    ).not.toBeInTheDocument();
  });

  test("private shell shows the module groups and the session identity", async () => {
    renderWithRouter(
      <AppShell onLogout={() => {}} user={authenticatedSession.user}>
        <div>Contenido</div>
      </AppShell>
    );

    expect(
      await screen.findByRole("navigation", { name: "Comunidad educativa" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Padres de familia" })
    ).toHaveAttribute("href", "/app/padres-de-familia");
    expect(screen.getByRole("button", { name: "Cuenta" })).toBeInTheDocument();
  });

  test("private shell logs out from the account menu", async () => {
    const user = userEvent.setup();
    const onLogout = vi.fn();
    renderWithRouter(
      <AppShell onLogout={onLogout} user={authenticatedSession.user}>
        <div>Contenido</div>
      </AppShell>
    );

    await user.click(screen.getByRole("button", { name: "Cuenta" }));
    await user.click(screen.getByRole("menuitem", { name: "Cerrar sesión" }));

    expect(onLogout).toHaveBeenCalledTimes(1);
  });

  test("confirms before closing every active session", async () => {
    const user = userEvent.setup();
    const onLogoutAll = vi.fn().mockResolvedValue(undefined);
    renderWithRouter(
      <AppShell
        onLogout={() => {}}
        onLogoutAll={onLogoutAll}
        user={authenticatedSession.user}
      >
        <div>Contenido</div>
      </AppShell>
    );

    await user.click(screen.getByRole("button", { name: "Cuenta" }));
    await user.click(
      screen.getByRole("menuitem", { name: /Cerrar sesiones en todos/i })
    );
    expect(
      screen.getByRole("heading", { name: "Cerrar todas las sesiones" })
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cerrar todas" }));

    expect(onLogoutAll).toHaveBeenCalledTimes(1);
  });

  test("returns to login when the server reports session expiry", async () => {
    authServiceMock.me.mockResolvedValueOnce(authenticatedSession);
    renderWithRouter(<App />, { route: "/app" });

    expect(await screen.findByText(/Buen día, Demo/i)).toBeInTheDocument();
    act(() => window.dispatchEvent(new Event("siga:session-expired")));

    expect(
      await screen.findByRole("heading", { name: /Iniciar sesión/i })
    ).toBeInTheDocument();
    // L4: el login explica por que se cerro la sesion.
    expect(
      screen.getByText(/Su sesión se cerró por inactividad/i)
    ).toBeInTheDocument();
  });

  test("renders login page", async () => {
    renderWithRouter(<App />, { route: "/login" });

    expect(
      await screen.findByRole("heading", { name: /Iniciar sesión/i })
    ).toBeInTheDocument();
    expect(
      screen.getAllByAltText(/Logotipo del INEBI de Salcaja/i)
    ).toHaveLength(1);
  });

  test("keeps submit disabled while the login form is incomplete", async () => {
    renderWithRouter(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    // El formulario no deja enviar vacio en vez de aceptar y luego reclamar:
    // el usuario ve antes de actuar que falta algo.
    expect(
      await screen.findByRole("button", { name: /Ingresar/i })
    ).toBeDisabled();
    expect(authServiceMock.login).not.toHaveBeenCalled();
  });

  test("redirects to dashboard after successful login", async () => {
    const user = userEvent.setup();
    authServiceMock.login.mockResolvedValueOnce(authenticatedSession.user);

    renderWithRouter(
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/app" element={<div>Dashboard listo</div>} />
        </Routes>
      </AuthProvider>,
      { route: "/login" }
    );

    await user.type(screen.getByRole("textbox", { name: /Usuario/i }), "admin");
    await user.type(screen.getByLabelText("Contraseña"), "demo-pass-123");
    await user.click(screen.getByRole("button", { name: /Ingresar/i }));

    expect(authServiceMock.csrf).toHaveBeenCalledTimes(1);
    expect(authServiceMock.login).toHaveBeenCalledWith({
      username: "admin",
      password: "demo-pass-123",
    });
    expect(await screen.findByText(/Dashboard listo/i)).toBeInTheDocument();
  });

  test("shows backend login error and stays on login", async () => {
    const user = userEvent.setup();
    authServiceMock.login.mockRejectedValueOnce(
      new Error("Credenciales invalidas.")
    );

    renderWithRouter(
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/app" element={<div>Dashboard listo</div>} />
        </Routes>
      </AuthProvider>,
      { route: "/login" }
    );

    await user.type(screen.getByRole("textbox", { name: /Usuario/i }), "admin");
    await user.type(screen.getByLabelText("Contraseña"), "incorrecta");
    await user.click(screen.getByRole("button", { name: /Ingresar/i }));

    expect(
      await screen.findByText(/Credenciales invalidas./i)
    ).toBeInTheDocument();
    expect(screen.queryByText(/Dashboard listo/i)).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Iniciar sesión/i })
    ).toBeInTheDocument();
  });

  test("shows temporary lockout alert when account is locked", async () => {
    const user = userEvent.setup();
    const lockedError = new Error(
      "Cuenta bloqueada temporalmente por intentos fallidos. Podrá intentarlo de nuevo a las 15:45."
    );
    lockedError.payload = {
      error: { detail: { code: ["account_locked"] } },
    };
    authServiceMock.login.mockRejectedValueOnce(lockedError);

    renderWithRouter(
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/app" element={<div>Dashboard listo</div>} />
        </Routes>
      </AuthProvider>,
      { route: "/login" }
    );

    await user.type(screen.getByRole("textbox", { name: /Usuario/i }), "admin");
    await user.type(screen.getByLabelText("Contraseña"), "cualquier-pass");
    await user.click(screen.getByRole("button", { name: /Ingresar/i }));

    // L5: se dice que es un bloqueo temporal y hasta cuando, no "credenciales invalidas".
    expect(
      await screen.findByText("Cuenta bloqueada temporalmente")
    ).toBeInTheDocument();
    expect(screen.getByText(/a las 15:45/)).toBeInTheDocument();
    expect(screen.queryByText(/Dashboard listo/i)).not.toBeInTheDocument();
  });

  test("renders 404 page", () => {
    renderWithRouter(<NotFoundPage />);
    expect(screen.getByText(/Página no encontrada/i)).toBeInTheDocument();
  });

  test("private route redirects when session missing", async () => {
    authServiceMock.me.mockResolvedValueOnce(anonymousSession);
    renderWithRouter(<App />, { route: "/app" });

    expect(
      await screen.findByRole("heading", { name: /Iniciar sesión/i })
    ).toBeInTheDocument();
  });

  test("private route renders dashboard when session exists", async () => {
    authServiceMock.me.mockResolvedValueOnce(authenticatedSession);
    vi.spyOn(apiClient, "get").mockResolvedValue({
      service: "api",
      status: "ok",
    });

    renderWithRouter(<App />, { route: "/app" });

    expect(await screen.findByText(/Buen día, Demo/i)).toBeInTheDocument();
  });

  test("does not store password or session token in localStorage on login", async () => {
    const user = userEvent.setup();
    const setItemSpy = vi.spyOn(Storage.prototype, "setItem");
    authServiceMock.csrf.mockResolvedValueOnce(undefined);
    authServiceMock.login.mockResolvedValueOnce(authenticatedSession.user);

    renderWithRouter(
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/app" element={<div>Privado</div>} />
        </Routes>
      </AuthProvider>,
      { route: "/login" }
    );

    await user.type(screen.getByRole("textbox", { name: /Usuario/i }), "admin");
    await user.type(screen.getByLabelText("Contraseña"), "admin");
    await user.click(screen.getByRole("button", { name: /Ingresar/i }));

    await waitFor(() => expect(authServiceMock.login).toHaveBeenCalled());
    // Nada de credenciales ni de sesion en localStorage: la sesion vive en la
    // cookie del backend. MUI si escribe la preferencia de tema, y eso no es
    // dato de sesion.
    const sessionWrites = setItemSpy.mock.calls.filter(
      ([key]) => key !== "mui-mode"
    );
    expect(sessionWrites).toHaveLength(0);
  });

  test("error boundary renders fallback", () => {
    function Bomb() {
      throw new Error("boom");
    }

    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    renderWithRouter(
      <AppErrorBoundary>
        <Bomb />
      </AppErrorBoundary>
    );

    expect(screen.getByRole("alert")).toHaveTextContent(/Error inesperado/i);
    consoleSpy.mockRestore();
  });
});
