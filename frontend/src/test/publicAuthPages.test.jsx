import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

const authServiceMock = vi.hoisted(() => ({
  me: vi.fn(),
  login: vi.fn(),
  logout: vi.fn(),
  csrf: vi.fn(),
  activate: vi.fn(),
  consumePasswordReset: vi.fn(),
  passwordPolicy: vi.fn(),
  changePassword: vi.fn(),
}));
vi.mock("@auth/authService.js", () => ({ authService: authServiceMock }));

import { ActivationPage } from "@auth/ActivationPage.jsx";
import { ChangePasswordWindow } from "@auth/ChangePasswordWindow.jsx";
import { LoginPage } from "@auth/LoginPage.jsx";
import { PasswordResetPage } from "@auth/PasswordResetPage.jsx";

import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import { renderWithSession } from "./helpers/renderWithSession.jsx";

const RULES = [
  "Su contraseña debe contener al menos 8 caracteres.",
  "Su contraseña no puede ser una clave utilizada comúnmente.",
];

function fieldError(message, field, messages) {
  const error = new Error(message);
  error.payload = { error: { detail: { [field]: messages } } };
  return error;
}

beforeEach(() => {
  Object.values(authServiceMock).forEach((fn) => fn.mockReset());
  authServiceMock.passwordPolicy.mockResolvedValue({ rules: RULES });
});

describe("LoginPage (L3, L6)", () => {
  test("el campo contraseña lleva tilde y se puede mostrar u ocultar", async () => {
    const user = userEvent.setup();
    renderWithSession(<LoginPage />, { user: null });

    const password = screen.getByLabelText("Contraseña");
    expect(password).toHaveAttribute("type", "password");
    await user.click(
      screen.getByRole("button", { name: "Mostrar contraseña" })
    );
    expect(password).toHaveAttribute("type", "text");
    await user.click(
      screen.getByRole("button", { name: "Ocultar contraseña" })
    );
    expect(password).toHaveAttribute("type", "password");
  });

  test("'¿Olvidó su contraseña?' explica que el enlace lo emite administración", async () => {
    const user = userEvent.setup();
    renderWithSession(<LoginPage />, { user: null });

    await user.click(
      screen.getByRole("button", { name: "¿Olvidó su contraseña?" })
    );

    expect(
      screen.getByText(/Pida a administración un enlace de restablecimiento/)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Recibí un código de activación" })
    ).toHaveAttribute("href", "/activar");
  });

  test("muestra el aviso de sesion cerrada por inactividad", () => {
    renderWithSession(<LoginPage />, { user: null, sessionNotice: "expired" });

    expect(
      screen.getByText(/Su sesión se cerró por inactividad/)
    ).toBeInTheDocument();
  });
});

describe("ActivationPage (L1, MC2)", () => {
  async function fill(user, password = "una-clave-larga-segura") {
    await user.type(
      screen.getByLabelText(/Usuario institucional/),
      "ana.lopez"
    );
    await user.type(screen.getByLabelText(/Código de activación/), "12345678");
    await user.type(screen.getByLabelText(/^Contraseña nueva/), password);
    await user.type(screen.getByLabelText(/^Confirmar contraseña/), password);
    await user.click(screen.getByRole("button", { name: "Activar cuenta" }));
  }

  test("lista las reglas reales y activa la cuenta", async () => {
    const user = userEvent.setup();
    authServiceMock.activate.mockResolvedValue({
      username: "ana.lopez",
      status: "active",
    });
    renderWithRouter(<ActivationPage />, { route: "/activar" });

    expect(await screen.findByText(RULES[0])).toBeInTheDocument();
    await fill(user);

    expect(authServiceMock.activate).toHaveBeenCalledWith({
      username: "ana.lopez",
      activation_code: "12345678",
      password: "una-clave-larga-segura",
    });
    expect(await screen.findByText("Cuenta activada")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Iniciar sesión" })
    ).toHaveAttribute("href", "/login");
  });

  test("muestra cada regla incumplida junto al campo contraseña", async () => {
    const user = userEvent.setup();
    authServiceMock.activate.mockRejectedValue(
      fieldError("Contraseña débil", "password", [
        "Esta contraseña es demasiado corta.",
        "Esta contraseña es demasiado común.",
      ])
    );
    renderWithRouter(<ActivationPage />, { route: "/activar" });

    await fill(user, "123");

    expect(
      await screen.findByText(
        "Esta contraseña es demasiado corta. Esta contraseña es demasiado común."
      )
    ).toBeInTheDocument();
  });

  test("no envia si la confirmacion no coincide", async () => {
    const user = userEvent.setup();
    renderWithRouter(<ActivationPage />, { route: "/activar" });

    await user.type(screen.getByLabelText(/Usuario institucional/), "ana");
    await user.type(screen.getByLabelText(/Código de activación/), "1");
    await user.type(screen.getByLabelText(/^Contraseña nueva/), "aaaa-bbbb");
    await user.type(screen.getByLabelText(/^Confirmar contraseña/), "otra");
    await user.click(screen.getByRole("button", { name: "Activar cuenta" }));

    expect(screen.getByText(/no coinciden/)).toBeInTheDocument();
    expect(authServiceMock.activate).not.toHaveBeenCalled();
  });
});

describe("PasswordResetPage (L2)", () => {
  test("sin token explica que el enlace esta incompleto", () => {
    renderWithRouter(<PasswordResetPage />, { route: "/restablecer" });

    expect(screen.getByText(/El enlace está incompleto/)).toBeInTheDocument();
  });

  test("usa el token del enlace y confirma el cambio", async () => {
    const user = userEvent.setup();
    authServiceMock.consumePasswordReset.mockResolvedValue(null);
    renderWithRouter(<PasswordResetPage />, {
      route: "/restablecer?token=abc123",
    });

    await user.type(
      screen.getByLabelText(/^Contraseña nueva/),
      "clave-nueva-123"
    );
    await user.type(
      screen.getByLabelText(/^Confirmar contraseña/),
      "clave-nueva-123"
    );
    await user.click(
      screen.getByRole("button", { name: "Guardar contraseña nueva" })
    );

    expect(authServiceMock.consumePasswordReset).toHaveBeenCalledWith({
      token: "abc123",
      password: "clave-nueva-123",
    });
    expect(
      await screen.findByText("Contraseña restablecida")
    ).toBeInTheDocument();
  });

  test("un enlace vencido muestra el mensaje del backend", async () => {
    const user = userEvent.setup();
    authServiceMock.consumePasswordReset.mockRejectedValue(
      new Error("El enlace de restablecimiento no es válido o ya venció.")
    );
    renderWithRouter(<PasswordResetPage />, {
      route: "/restablecer?token=vencido",
    });

    await user.type(screen.getByLabelText(/^Contraseña nueva/), "x");
    await user.type(screen.getByLabelText(/^Confirmar contraseña/), "x");
    await user.click(
      screen.getByRole("button", { name: "Guardar contraseña nueva" })
    );

    expect(
      await screen.findByText(/no es válido o ya venció/)
    ).toBeInTheDocument();
  });
});

describe("ChangePasswordWindow (MC2)", () => {
  test("muestra las reglas reales y el error de cada campo", async () => {
    const user = userEvent.setup();
    authServiceMock.changePassword.mockRejectedValue(
      fieldError("No cumple", "new_password", [
        "La contraseña es demasiado parecida al usuario.",
      ])
    );
    renderWithRouter(<ChangePasswordWindow onClose={vi.fn()} open />);

    expect(await screen.findByText(RULES[1])).toBeInTheDocument();
    expect(
      screen.queryByText("Debe contener al menos 8 caracteres.")
    ).not.toBeInTheDocument();
    await user.type(screen.getByLabelText(/Contraseña actual/), "actual-1234");
    await user.type(screen.getByLabelText(/^Nueva contraseña/), "admin-admin");
    await user.type(
      screen.getByLabelText(/Confirmar nueva contraseña/),
      "admin-admin"
    );
    await user.click(
      screen.getByRole("button", { name: /Actualizar contraseña/ })
    );

    expect(
      await screen.findByText("La contraseña es demasiado parecida al usuario.")
    ).toBeInTheDocument();
  });
});
