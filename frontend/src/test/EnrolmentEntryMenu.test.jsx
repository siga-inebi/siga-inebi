import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";

import { EnrolmentEntryMenu } from "@enrolments/EnrolmentEntryMenu.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

test.each([
  [/Un estudiante/, "onIndividual"],
  [/Altas iniciales por lotes/, "onInitialBulk"],
  [/Reinscribir por lotes/, "onReenrolBulk"],
])(
  "conserva el flujo elegido desde un solo acceso: %s",
  async (label, prop) => {
    const actions = {
      onIndividual: vi.fn(),
      onInitialBulk: vi.fn(),
      onReenrolBulk: vi.fn(),
    };
    const user = userEvent.setup();
    renderWithRouter(<EnrolmentEntryMenu {...actions} />);
    expect(screen.getAllByRole("button")).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: "Matricular" }));
    await user.click(screen.getByRole("menuitem", { name: label }));
    expect(actions[prop]).toHaveBeenCalledTimes(1);
    for (const [name, action] of Object.entries(actions)) {
      if (name !== prop) expect(action).not.toHaveBeenCalled();
    }
    await waitFor(() =>
      expect(screen.queryByRole("menu")).not.toBeInTheDocument()
    );
  }
);

test("omite flujos no conectados y permite cerrar sin ejecutar acciones", async () => {
  const onIndividual = vi.fn();
  const onInitialBulk = vi.fn();
  const user = userEvent.setup();
  renderWithRouter(
    <EnrolmentEntryMenu
      onIndividual={onIndividual}
      onInitialBulk={onInitialBulk}
    />
  );
  const button = screen.getByRole("button", { name: "Matricular" });
  await user.click(button);
  expect(
    screen.queryByRole("menuitem", { name: /Reinscribir por lotes/ })
  ).not.toBeInTheDocument();
  await user.keyboard("{Escape}");
  await waitFor(() =>
    expect(screen.queryByRole("menu")).not.toBeInTheDocument()
  );
  expect(onIndividual).not.toHaveBeenCalled();
  expect(onInitialBulk).not.toHaveBeenCalled();
  expect(button).toHaveFocus();
});
