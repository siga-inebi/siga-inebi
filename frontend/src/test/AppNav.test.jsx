import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { AppNav } from "../layouts/AppNav.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const studentsServiceMock = vi.hoisted(() => ({ list: vi.fn() }));
const teachersServiceMock = vi.hoisted(() => ({ list: vi.fn() }));
const guardiansServiceMock = vi.hoisted(() => ({ list: vi.fn() }));

vi.mock("../services/studentsService.js", () => ({
  studentsService: studentsServiceMock,
}));
vi.mock("../services/teachersService.js", () => ({
  teachersService: teachersServiceMock,
}));
vi.mock("../services/guardiansService.js", () => ({
  guardiansService: guardiansServiceMock,
}));

describe("AppNav", () => {
  beforeEach(() => {
    studentsServiceMock.list.mockReset().mockResolvedValue([]);
    teachersServiceMock.list.mockReset().mockResolvedValue([]);
    guardiansServiceMock.list.mockReset().mockResolvedValue([]);
  });

  test("renders a home link plus the LISTADOS group with a link to each domain", async () => {
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
    expect(await screen.findAllByText("0")).toHaveLength(3);
  });

  test("renders the CATALOGO ACADEMICO group with a link to each catalog page", async () => {
    renderWithRouter(<AppNav user={{ id: 1 }} />);

    expect(await screen.findByText("Catalogo academico")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sedes" })).toHaveAttribute(
      "href",
      "/app/sedes"
    );
    expect(screen.getByRole("link", { name: "Niveles" })).toHaveAttribute(
      "href",
      "/app/niveles"
    );
    expect(screen.getByRole("link", { name: "Cursos" })).toHaveAttribute(
      "href",
      "/app/cursos"
    );
  });

  test("shows a badge with the real count once the domain services resolve", async () => {
    studentsServiceMock.list.mockResolvedValue(new Array(8).fill({}));
    renderWithRouter(<AppNav user={{ id: 1 }} />);

    expect(
      await screen.findByRole("link", { name: "Alumnos" })
    ).toHaveTextContent("8");
    expect(screen.getByRole("link", { name: "Docentes" })).toHaveTextContent(
      "0"
    );
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

    expect(screen.getByRole("complementary")).toHaveClass("sidebar-collapsed");
    expect(
      screen.getByRole("button", { name: "Expandir navegacion" })
    ).toBeInTheDocument();
    // Accessible names stay stable even while collapsed (labels hide via CSS,
    // not by leaving the DOM).
    expect(screen.getByRole("link", { name: "Alumnos" })).toBeInTheDocument();
  });
});
