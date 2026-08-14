import { screen, within } from "@testing-library/react";

import { Sidebar } from "@layout/Sidebar.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const USER = { id: 1 };

describe("Sidebar", () => {
  test("renders the home link plus one labelled nav group per section", () => {
    renderWithRouter(<Sidebar user={USER} />);

    expect(screen.getByRole("link", { name: "Panel" })).toHaveAttribute(
      "href",
      "/app"
    );

    for (const group of [
      "Comunidad educativa",
      "Estructura academica",
      "Operacion diaria",
      "Documentos y control",
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
    expect(within(nav).getByRole("link", { name: "Personas" })).toHaveAttribute(
      "href",
      "/app/personas"
    );
  });

  test("links every academic-structure module to its route", () => {
    renderWithRouter(<Sidebar user={USER} />);
    const nav = screen.getByRole("navigation", {
      name: "Estructura academica",
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
      name: "Operacion diaria",
    });
    for (const [label, href] of [
      ["Matriculas", "/app/matriculas"],
      ["Asistencia", "/app/asistencia"],
      ["Evaluacion", "/app/evaluacion"],
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

    // Colapsado solo se ve el icono, pero el nombre accesible sigue ahi via
    // tooltip/aria: un lector de pantalla no debe perder la navegacion.
    expect(
      screen.getByRole("link", { name: "Estudiantes" })
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Panel" })).toBeInTheDocument();
  });
});
