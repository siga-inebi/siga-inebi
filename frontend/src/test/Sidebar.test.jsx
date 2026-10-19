import { screen, within } from "@testing-library/react";

import { Sidebar } from "@layout/Sidebar.jsx";
import { ALL_PERMISSIONS } from "./fixtures/auth.js";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const USER = { public_id: "u-1", permissions: ALL_PERMISSIONS };

describe("Sidebar", () => {
  test("renders the home link plus one labelled nav group per section", () => {
    renderWithRouter(<Sidebar user={USER} />);

    expect(screen.getByRole("link", { name: "Panel" })).toHaveAttribute(
      "href",
      "/app"
    );

    for (const group of [
      "Comunidad educativa",
      "Estructura académica",
      "Operación diaria",
      "Documentos y control",
      "Administración",
    ]) {
      expect(
        screen.getByRole("navigation", { name: group })
      ).toBeInTheDocument();
    }
  });

  test("links every community module to its route", () => {
    renderWithRouter(<Sidebar user={USER} />);
    const nav = screen.getByRole("navigation", { name: "Comunidad educativa" });

    expect(
      within(nav).getByRole("link", { name: "Estudiantes" })
    ).toHaveAttribute("href", "/app/alumnos");
    expect(within(nav).getByRole("link", { name: "Docentes" })).toHaveAttribute(
      "href",
      "/app/docentes"
    );
    expect(
      within(nav).getByRole("link", { name: "Padres de familia" })
    ).toHaveAttribute("href", "/app/padres-de-familia");
  });

  test("links every academic-structure module to its route", () => {
    renderWithRouter(<Sidebar user={USER} />);
    const nav = screen.getByRole("navigation", {
      name: "Estructura académica",
    });

    for (const [label, href] of [
      ["Ciclo escolar", "/app/ciclos"],
      ["Sedes", "/app/sedes"],
      ["Niveles", "/app/niveles"],
      ["Cursos", "/app/cursos"],
      ["Asignaciones docentes", "/app/asignaciones"],
    ]) {
      expect(within(nav).getByRole("link", { name: label })).toHaveAttribute(
        "href",
        href
      );
    }
  });

  test("links the daily-operation and control modules added with their backends", () => {
    renderWithRouter(<Sidebar user={USER} />);

    const operation = screen.getByRole("navigation", {
      name: "Operación diaria",
    });
    for (const [label, href] of [
      ["Matrículas", "/app/matriculas"],
      ["Asistencia", "/app/asistencia"],
      ["Evaluación", "/app/evaluacion"],
    ]) {
      expect(
        within(operation).getByRole("link", { name: label })
      ).toHaveAttribute("href", href);
    }

    const control = screen.getByRole("navigation", {
      name: "Documentos y control",
    });
    expect(
      within(control).getByRole("link", { name: "Plantillas" })
    ).toHaveAttribute("href", "/app/plantillas");
    expect(
      within(control).getByRole("link", { name: "Alertas" })
    ).toHaveAttribute("href", "/app/alertas");
  });

  test("groups administration modules under Administración (2.17.6)", () => {
    renderWithRouter(<Sidebar user={USER} />);
    const nav = screen.getByRole("navigation", { name: "Administración" });

    for (const [label, href] of [
      ["Cuentas", "/app/cuentas"],
      ["Roles", "/app/roles"],
      ["Personas", "/app/personas"],
      ["Tipos de documento", "/app/tipos-documento"],
      ["Auditoría", "/app/auditoria"],
      ["Plataforma", "/app/plataforma"],
    ]) {
      expect(within(nav).getByRole("link", { name: label })).toHaveAttribute(
        "href",
        href
      );
    }
  });

  test("hides modules and the Administración group without their permissions (1.4)", () => {
    renderWithRouter(<Sidebar user={{ public_id: "u-2", permissions: [] }} />);

    // Sin permiso atomico que lo controle, el modulo se muestra a toda sesion.
    expect(screen.getByRole("link", { name: "Docentes" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sedes" })).toBeInTheDocument();
    // Con permiso atomico, sin el no aparece.
    expect(
      screen.queryByRole("link", { name: "Estudiantes" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Alertas" })
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: "Administración" })
    ).not.toBeInTheDocument();
  });

  test("shows only the administration modules the account can use", () => {
    renderWithRouter(
      <Sidebar
        user={{ public_id: "u-3", permissions: ["audit.read", "role.assign"] }}
      />
    );
    const nav = screen.getByRole("navigation", { name: "Administración" });

    expect(
      within(nav).getByRole("link", { name: "Auditoría" })
    ).toBeInTheDocument();
    expect(
      within(nav).getByRole("link", { name: "Roles" })
    ).toBeInTheDocument();
    expect(
      within(nav).queryByRole("link", { name: "Cuentas" })
    ).not.toBeInTheDocument();
    expect(
      within(nav).queryByRole("link", { name: "Plataforma" })
    ).not.toBeInTheDocument();
  });

  test("a superuser sees every module", () => {
    renderWithRouter(
      <Sidebar
        user={{ public_id: "u-4", is_superuser: true, permissions: [] }}
      />
    );

    expect(
      screen.getByRole("link", { name: "Plataforma" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Estudiantes" })
    ).toBeInTheDocument();
  });

  test("shows the count badge only on the modules that report one", () => {
    renderWithRouter(
      <Sidebar counts={{ alumnos: 8, docentes: 0 }} user={USER} />
    );

    expect(screen.getByRole("link", { name: /Estudiantes/ })).toHaveTextContent(
      "8"
    );
    expect(screen.getByRole("link", { name: /Docentes/ })).toHaveTextContent(
      "0"
    );
    // Personas no declara `countable`, asi que no lleva insignia.
    expect(
      screen.getByRole("link", { name: /Personas/ })
    ).not.toHaveTextContent(/\d/);
  });

  test("keeps accessible names when collapsed", () => {
    renderWithRouter(<Sidebar collapsed user={USER} />);

    expect(
      screen.getByRole("link", { name: "Estudiantes" })
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Panel" })).toBeInTheDocument();
  });
});
