import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { ChangePasswordWindow } from "@auth/ChangePasswordWindow.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const authServiceMock = vi.hoisted(() => ({
  changePassword: vi.fn(),
}));

vi.mock("@auth/authService.js", () => ({
  authService: authServiceMock,
}));

describe("ChangePasswordWindow", () => {
  test("renders modal when open and submits valid password change", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    const onSuccess = vi.fn();
    authServiceMock.changePassword.mockResolvedValueOnce({
      status: "ok",
      message: "Contraseña actualizada exitosamente.",
    });

    renderWithRouter(
      <ChangePasswordWindow
        onClose={onClose}
        onSuccess={onSuccess}
        open={true}
      />
    );

    expect(screen.getByText(/Cambiar contraseña/i)).toBeInTheDocument();

    await user.type(
      screen.getByLabelText(/Contraseña actual/i),
      "Current-Password-123!"
    );
    await user.type(
      screen.getByLabelText(/^Nueva contraseña/i),
      "New-Secret-Password-2026!"
    );
    await user.type(
      screen.getByLabelText(/Confirmar nueva contraseña/i),
      "New-Secret-Password-2026!"
    );

    await user.click(
      screen.getByRole("button", { name: /Actualizar contraseña/i })
    );

    await waitFor(() => {
      expect(authServiceMock.changePassword).toHaveBeenCalledWith({
        current_password: "Current-Password-123!",
        new_password: "New-Secret-Password-2026!",
        new_password_confirm: "New-Secret-Password-2026!",
      });
    });

    expect(
      await screen.findByText(/Contraseña actualizada exitosamente/i)
    ).toBeInTheDocument();
    expect(onSuccess).toHaveBeenCalled();
  });

  test("validates password mismatch on client side without calling API", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();

    renderWithRouter(<ChangePasswordWindow onClose={onClose} open={true} />);

    await user.type(
      screen.getByLabelText(/Contraseña actual/i),
      "Current-Password-123!"
    );
    await user.type(
      screen.getByLabelText(/^Nueva contraseña/i),
      "New-Secret-Password-2026!"
    );
    await user.type(
      screen.getByLabelText(/Confirmar nueva contraseña/i),
      "Different-Password-999!"
    );

    await user.click(
      screen.getByRole("button", { name: /Actualizar contraseña/i })
    );

    expect(await screen.findByText(/no coinciden/i)).toBeInTheDocument();
    expect(authServiceMock.changePassword).not.toHaveBeenCalled();
  });

  test("displays backend error message when current password is wrong", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    authServiceMock.changePassword.mockRejectedValueOnce(
      new Error("La contraseña actual es incorrecta.")
    );

    renderWithRouter(<ChangePasswordWindow onClose={onClose} open={true} />);

    await user.type(
      screen.getByLabelText(/Contraseña actual/i),
      "Wrong-Password"
    );
    await user.type(
      screen.getByLabelText(/^Nueva contraseña/i),
      "New-Secret-Password-2026!"
    );
    await user.type(
      screen.getByLabelText(/Confirmar nueva contraseña/i),
      "New-Secret-Password-2026!"
    );

    await user.click(
      screen.getByRole("button", { name: /Actualizar contraseña/i })
    );

    expect(
      await screen.findByText(/La contraseña actual es incorrecta/i)
    ).toBeInTheDocument();
  });
});
