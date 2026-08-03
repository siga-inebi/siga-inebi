import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AppNav } from "../layouts/AppNav.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

describe("AppNav", () => {
  test("renders a home link plus the LISTADOS group with a link to each domain", () => {
    renderWithRouter(<AppNav user={{ id: 1 }} />);

    expect(
      screen.getByRole("link", { name: "Panel principal" })
    ).toHaveAttribute("href", "/app");
    expect(screen.getByText("Listados")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Alumnos" })).toHaveAttribute(
      "href",
      "/app/alumnos"
    );
    expect(screen.getByRole("link", { name: "Docentes" })).toHaveAttribute(
      "href",
      "/app/docentes"
    );
    expect(
      screen.getByRole("link", { name: "Padres de familia" })
    ).toHaveAttribute("href", "/app/padres-de-familia");
  });

  test("shows a badge only for items with a known count", () => {
    renderWithRouter(<AppNav counts={{ alumnos: 8 }} user={{ id: 1 }} />);

    expect(screen.getByRole("link", { name: "Alumnos" })).toHaveTextContent(
      "8"
    );
    expect(
      screen.getByRole("link", { name: "Docentes" })
    ).not.toHaveTextContent(/\d/);
  });

  test("collapses and expands via the toggle button", async () => {
    const user = userEvent.setup();
    renderWithRouter(<AppNav user={{ id: 1 }} />);

    const toggle = screen.getByRole("button", {
      name: "Colapsar navegacion",
    });
    expect(screen.getByRole("complementary")).not.toHaveClass(
      "sidebar-collapsed"
    );

    await user.click(toggle);

    expect(screen.getByRole("complementary")).toHaveClass(
      "sidebar-collapsed"
    );
    expect(
      screen.getByRole("button", { name: "Expandir navegacion" })
    ).toBeInTheDocument();
    // Accessible names stay stable even while collapsed (labels hide via CSS,
    // not by leaving the DOM).
    expect(
      screen.getByRole("link", { name: "Alumnos" })
    ).toBeInTheDocument();
  });
});
