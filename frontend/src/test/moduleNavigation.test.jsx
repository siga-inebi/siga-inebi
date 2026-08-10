import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("../services/authService", async () => {
  const { authServiceMock } = await import("./mocks/authService.js");
  return { authService: authServiceMock };
});

vi.mock("../services/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});

vi.mock("../services/peopleService.js", async () => {
  const { peopleServiceMock } = await import("./mocks/peopleService.js");
  return { peopleService: peopleServiceMock };
});

import { App } from "../app/App.jsx";
import { apiClient } from "../services/apiClient.js";
import { authenticatedSession, anonymousSession } from "./fixtures/auth.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import { resetAcademicsServiceMock } from "./mocks/academicsService.js";
import { authServiceMock } from "./mocks/authService.js";
import { resetPeopleServiceMock } from "./mocks/peopleService.js";

describe("navegacion de modulos", () => {
  beforeEach(() => {
    resetAcademicsServiceMock();
    resetPeopleServiceMock();
    authServiceMock.me.mockResolvedValue(authenticatedSession);
    vi.spyOn(apiClient, "get").mockResolvedValue({
      service: "api",
      status: "ok",
    });
  });

  test("una sesion abierta ve los modulos del catalogo", async () => {
    renderWithRouter(<App />, { route: "/app" });

    expect(
      await screen.findByRole("link", { name: "Panel principal" })
    ).toBeInTheDocument();

    for (const label of ["Personas", "Sedes", "Niveles", "Cursos"]) {
      expect(screen.getAllByRole("link", { name: label }).length).toBeGreaterThan(0);
    }
  });

  test("una sesion anonima no ve los modulos privados", async () => {
    authServiceMock.me.mockResolvedValue(anonymousSession);
    renderWithRouter(<App />, { route: "/" });

    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Abrir menu" }));

    expect(
      await screen.findByRole("link", { name: /Iniciar sesion/i })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: "Catalogo academico" })
    ).not.toBeInTheDocument();
  });

  test("navega desde el panel hasta la pantalla de sedes", async () => {
    const user = userEvent.setup();
    renderWithRouter(<App />, { route: "/app" });

    const nav = await screen.findByRole("navigation", {
      name: "Catalogo academico",
    });
    await user.click(within(nav).getByRole("link", { name: "Sedes" }));

    expect(
      await screen.findByRole("heading", { name: "Sedes y jornadas" })
    ).toBeInTheDocument();
  });

  test("navega desde el panel hasta la pantalla de personas", async () => {
    const user = userEvent.setup();
    renderWithRouter(<App />, { route: "/app" });

    await user.click(await screen.findByRole("link", { name: "Personas" }));

    expect(
      await screen.findByRole("heading", { name: "Personas" })
    ).toBeInTheDocument();
  });

  test("cada ruta privada del catalogo monta su pantalla", async () => {
    renderWithRouter(<App />, { route: "/app/niveles" });
    expect(
      await screen.findByRole("heading", {
        name: "Niveles, grados y plan de estudios",
      })
    ).toBeInTheDocument();
  });

  test("la ruta de cursos exige sesion", async () => {
    authServiceMock.me.mockResolvedValue(anonymousSession);
    renderWithRouter(<App />, { route: "/app/cursos" });

    expect(
      await screen.findByRole("heading", { name: /Iniciar sesion/i })
    ).toBeInTheDocument();
  });
});
