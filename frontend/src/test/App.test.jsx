import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { App } from "../app/App.jsx";
import { AppErrorBoundary } from "../components/AppErrorBoundary.jsx";
import { AuthProvider } from "../features/auth/AuthContext.jsx";
import { AppLayout } from "../layouts/AppLayout.jsx";
import { LoginPage } from "../pages/LoginPage.jsx";
import { NotFoundPage } from "../pages/NotFoundPage.jsx";
import { apiClient } from "../services/apiClient.js";
import { authenticatedSession, anonymousSession } from "./fixtures/auth.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const authServiceMock = vi.hoisted(() => ({
  me: vi.fn().mockResolvedValue({ authenticated: false, user: null }),
  login: vi.fn(),
  logout: vi.fn(),
  csrf: vi.fn(),
}));

vi.mock("../services/authService", () => ({
  authService: authServiceMock,
}));

describe("app shell", () => {
  beforeEach(() => {
    authServiceMock.me.mockResolvedValue(anonymousSession);
    authServiceMock.csrf.mockResolvedValue(undefined);
    authServiceMock.login.mockResolvedValue(authenticatedSession.user);
    authServiceMock.logout.mockResolvedValue(undefined);
  });

  test("renders home screen", async () => {
    authServiceMock.me.mockResolvedValueOnce(anonymousSession);
    renderWithRouter(<App />);

    expect(
      await screen.findByText(/Control academico, administrativo y operativo/i)
    ).toBeInTheDocument();
  });

  test("renders layout actions", async () => {
    renderWithRouter(
      <AuthProvider>
        <AppLayout>
          <div>Contenido</div>
        </AppLayout>
      </AuthProvider>
    );

    expect(await screen.findByText("SIGA-INEBI")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Iniciar sesion/i })
    ).toBeInTheDocument();
  });

  test("renders login page", async () => {
    renderWithRouter(<App />, { route: "/login" });
    expect(
      await screen.findByRole("heading", { name: /Iniciar sesion/i })
    ).toBeInTheDocument();
    expect(screen.getAllByAltText(/Logo de INEBI Salcaja/i)).toHaveLength(2);
  });

  test("validates empty login form", async () => {
    const user = userEvent.setup();
    renderWithRouter(
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    );

    await user.click(screen.getByRole("button", { name: /Entrar al sistema/i }));

    expect(
      screen.getByText(/Ingrese usuario y contrasena/i)
    ).toBeInTheDocument();
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
    await user.type(screen.getByLabelText(/Contrasena/i), "demo-pass-123");
    await user.click(screen.getByRole("button", { name: /Entrar al sistema/i }));

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
    await user.type(screen.getByLabelText(/Contrasena/i), "incorrecta");
    await user.click(screen.getByRole("button", { name: /Entrar al sistema/i }));

    expect(
      await screen.findByText(/Credenciales invalidas./i)
    ).toBeInTheDocument();
    expect(screen.queryByText(/Dashboard listo/i)).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /Iniciar sesion/i })
    ).toBeInTheDocument();
  });

  test("renders 404 page", () => {
    renderWithRouter(<NotFoundPage />);
    expect(screen.getByText("404")).toBeInTheDocument();
  });

  test("private route redirects when session missing", async () => {
    authServiceMock.me.mockResolvedValueOnce(anonymousSession);
    renderWithRouter(<App />, { route: "/app" });

    expect(
      await screen.findByRole("heading", { name: /Iniciar sesion/i })
    ).toBeInTheDocument();
  });

  test("private route renders dashboard when session exists", async () => {
    authServiceMock.me.mockResolvedValueOnce(authenticatedSession);
    vi.spyOn(apiClient, "get").mockResolvedValue({
      service: "api",
      status: "ok",
    });

    renderWithRouter(<App />, { route: "/app" });

    expect(await screen.findByText(/Bienvenido, Demo./i)).toBeInTheDocument();
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
    await user.type(screen.getByLabelText(/Contrasena/i), "admin");
    await user.click(screen.getByRole("button", { name: /Entrar al sistema/i }));

    await waitFor(() => expect(authServiceMock.login).toHaveBeenCalled());
    expect(setItemSpy).not.toHaveBeenCalled();
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
