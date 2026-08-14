import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

vi.mock("@auth/authService.js", async () => {
  const { authServiceMock } = await import("./mocks/authService.js");
  return { authService: authServiceMock };
});

vi.mock("@academics/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});

vi.mock("@people/peopleService.js", async () => {
  const { peopleServiceMock } = await import("./mocks/peopleService.js");
  return { peopleService: peopleServiceMock };
});

const studentsServiceMock = vi.hoisted(() => ({ list: vi.fn() }));
const teachersServiceMock = vi.hoisted(() => ({ list: vi.fn() }));
const guardiansServiceMock = vi.hoisted(() => ({ list: vi.fn() }));

vi.mock("@students/studentsService.js", () => ({
  studentsService: studentsServiceMock,
}));

vi.mock("@teachers/teachersService.js", () => ({
  teachersService: teachersServiceMock,
}));

vi.mock("@guardians/guardiansService.js", () => ({
  guardiansService: guardiansServiceMock,
}));

import { App } from "../app/App.jsx";
import { apiClient } from "@shared/api/apiClient.js";
import { authenticatedSession, anonymousSession } from "./fixtures/auth.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import { resetAcademicsServiceMock } from "./mocks/academicsService.js";
import { authServiceMock } from "./mocks/authService.js";
import { resetPeopleServiceMock } from "./mocks/peopleService.js";

describe("navegacion de modulos", () => {
  beforeEach(() => {
    resetAcademicsServiceMock();
    resetPeopleServiceMock();
    studentsServiceMock.list.mockReset().mockResolvedValue([]);
    teachersServiceMock.list.mockReset().mockResolvedValue([]);
    guardiansServiceMock.list.mockReset().mockResolvedValue([]);
    authServiceMock.me.mockResolvedValue(authenticatedSession);
    vi.spyOn(apiClient, "get").mockResolvedValue({
      service: "api",
      status: "ok",
    });
  });

  test("una sesion abierta ve los modulos del catalogo", async () => {
    renderWithRouter(<App />, { route: "/app" });

    expect(await screen.findByRole("link", { name: "Panel" })).toBeInTheDocument();

    for (const label of ["Personas", "Sedes", "Niveles", "Cursos"]) {
      expect(screen.getAllByRole("link", { name: label }).length).toBeGreaterThan(0);
    }
  });

  test("una sesion anonima no ve los modulos privados", async () => {
    authServiceMock.me.mockResolvedValue(anonymousSession);
    renderWithRouter(<App />, { route: "/" });

    expect(
      await screen.findByRole("link", { name: /Iniciar sesion/i })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: "Estructura academica" })
    ).not.toBeInTheDocument();
  });

  test("navega desde el panel hasta la pantalla de sedes", async () => {
    const user = userEvent.setup();
    renderWithRouter(<App />, { route: "/app" });

    const nav = await screen.findByRole("navigation", {
      name: "Estructura academica",
    });
    await user.click(within(nav).getByRole("link", { name: "Sedes" }));

    expect(
      await screen.findByRole("heading", { name: "Sedes y jornadas" })
    ).toBeInTheDocument();
  });

  test("navega desde el panel hasta la pantalla de personas", async () => {
    const user = userEvent.setup();
    renderWithRouter(<App />, { route: "/app" });

    const nav = await screen.findByRole("navigation", { name: "Comunidad educativa" });
    await user.click(within(nav).getByRole("link", { name: "Personas" }));

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

  test.each([
    ["/app/alumnos", "Estudiantes"],
    ["/app/docentes", "Docentes y administrativos"],
    ["/app/padres-de-familia", "Padres de familia"],
  ])("la ruta privada %s monta su pantalla", async (route, heading) => {
    renderWithRouter(<App />, { route });

    expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
  });

  test.each([
    ["/app/ciclos", "Ciclo escolar"],
    ["/app/matriculas", "Matriculas"],
    ["/app/asistencia", "Asistencia"],
    ["/app/evaluacion", "Configuracion de evaluacion"],
    ["/app/plantillas", "Plantillas documentales"],
    ["/app/alertas", "Alertas"],
    ["/app/asignaciones", "Asignaciones docentes"],
  ])("la ruta privada %s monta su pantalla", async (route, heading) => {
    renderWithRouter(<App />, { route });

    expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
  });

  test.each(["/app/alumnos", "/app/docentes", "/app/padres-de-familia"])(
    "la ruta privada %s exige sesion",
    async (route) => {
      authServiceMock.me.mockResolvedValue(anonymousSession);
      renderWithRouter(<App />, { route });

      expect(
        await screen.findByRole("heading", { name: /Iniciar sesion/i })
      ).toBeInTheDocument();
    }
  );

  test.each(["/app/cursos", "/app/matriculas", "/app/asistencia", "/app/alertas"])(
    "la ruta privada %s exige sesion",
    async (route) => {
      authServiceMock.me.mockResolvedValue(anonymousSession);
      renderWithRouter(<App />, { route });

      expect(
        await screen.findByRole("heading", { name: /Iniciar sesion/i })
      ).toBeInTheDocument();
    }
  );
});
