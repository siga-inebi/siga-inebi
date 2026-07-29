import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { App } from "../app/App";

vi.mock("../services/authService", () => ({
  authService: {
    me: vi.fn().mockResolvedValue({ authenticated: false, user: null }),
    login: vi.fn(),
    logout: vi.fn(),
  },
}));

test("renders home screen", async () => {
  render(
    <MemoryRouter>
      <App />
    </MemoryRouter>
  );

  expect(await screen.findByText(/Gestion institucional modular/i)).toBeInTheDocument();
});
