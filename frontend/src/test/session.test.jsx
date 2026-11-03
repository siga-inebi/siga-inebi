import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider } from "@mui/material/styles";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

const authServiceMock = vi.hoisted(() => ({
  me: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  logoutAll: vi.fn(),
  csrf: vi.fn(),
}));
vi.mock("@auth/authService.js", () => ({ authService: authServiceMock }));

import { AuthProvider } from "@auth/AuthProvider.jsx";
import { LoginPage } from "@auth/LoginPage.jsx";
import { useAuth } from "@auth/useAuth.js";
import { API_ACTIVITY_EVENT } from "@shared/api/apiClient.js";
import { theme } from "@theme/theme.js";

import { sessionUser } from "./helpers/renderWithSession.jsx";

function Probe() {
  const { user, sessionNotice } = useAuth();
  return (
    <div>
      <span>{user ? `sesion:${user.username}` : "sin sesion"}</span>
      <span>{sessionNotice ? `aviso:${sessionNotice}` : ""}</span>
    </div>
  );
}

function renderProvider(ui = <Probe />, initialEntries = ["/"]) {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <ThemeProvider theme={theme}>
        <MemoryRouter initialEntries={initialEntries}>
          <AuthProvider>{ui}</AuthProvider>
        </MemoryRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

describe("aviso y vencimiento de sesion por inactividad (ux-ui L4)", () => {
  beforeEach(() => {
    // Solo el reloj y el intervalo son falsos: las esperas de Testing Library
    // siguen usando `setTimeout` real.
    vi.useFakeTimers({ toFake: ["Date", "setInterval", "clearInterval"] });
    authServiceMock.me.mockResolvedValue({
      authenticated: true,
      user: sessionUser([], { session_idle_timeout_minutes: 3 }),
    });
    authServiceMock.logout.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  test("avisa dos minutos antes y 'Seguir conectado' renueva la sesion", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    renderProvider();
    expect(await screen.findByText("sesion:admin")).toBeInTheDocument();
    expect(
      screen.queryByText("Su sesión está por cerrarse")
    ).not.toBeInTheDocument();

    act(() => vi.advanceTimersByTime(61_000));

    expect(
      await screen.findByText("Su sesión está por cerrarse")
    ).toBeInTheDocument();
    expect(screen.getByText("1:59")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Seguir conectado" }));

    await waitFor(() =>
      expect(
        screen.queryByText("Su sesión está por cerrarse")
      ).not.toBeInTheDocument()
    );
    expect(authServiceMock.me).toHaveBeenCalledTimes(2);
  });

  test("cada respuesta del servidor reinicia la cuenta regresiva", async () => {
    renderProvider();
    expect(await screen.findByText("sesion:admin")).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(55_000));
    act(() => window.dispatchEvent(new CustomEvent(API_ACTIVITY_EVENT)));
    act(() => vi.advanceTimersByTime(55_000));

    expect(
      screen.queryByText("Su sesión está por cerrarse")
    ).not.toBeInTheDocument();
  });

  test("al vencer cierra la sesion local y deja el aviso para el login", async () => {
    renderProvider();
    expect(await screen.findByText("sesion:admin")).toBeInTheDocument();

    act(() => vi.advanceTimersByTime(3 * 60_000 + 1_000));

    expect(await screen.findByText("sin sesion")).toBeInTheDocument();
    expect(screen.getByText("aviso:expired")).toBeInTheDocument();
    expect(authServiceMock.logout).toHaveBeenCalled();
  });

  test("el aviso del servidor (401 con X-SIGA-Session-Expired) tambien lo explica", async () => {
    renderProvider();
    expect(await screen.findByText("sesion:admin")).toBeInTheDocument();

    act(() => window.dispatchEvent(new Event("siga:session-expired")));

    expect(await screen.findByText("aviso:expired")).toBeInTheDocument();
  });
});

describe("volver a la misma pagina al entrar de nuevo (ux-ui L4)", () => {
  test("el login regresa a la ruta y busqueda de donde vino", async () => {
    const user = userEvent.setup();
    authServiceMock.me.mockResolvedValue({ authenticated: false, user: null });
    authServiceMock.csrf.mockResolvedValue(undefined);
    authServiceMock.login.mockResolvedValue(sessionUser());

    renderProvider(
      <Routes>
        <Route element={<LoginPage />} path="/login" />
        <Route element={<div>Cuentas filtradas</div>} path="/app/cuentas" />
      </Routes>,
      [
        {
          pathname: "/login",
          state: {
            from: { pathname: "/app/cuentas", search: "?status=active" },
          },
        },
      ]
    );

    await user.type(
      await screen.findByRole("textbox", { name: /Usuario/i }),
      "admin"
    );
    await user.type(screen.getByLabelText("Contraseña"), "clave-segura");
    await user.click(screen.getByRole("button", { name: "Ingresar" }));

    expect(await screen.findByText("Cuentas filtradas")).toBeInTheDocument();
  });
});
