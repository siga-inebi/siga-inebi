import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { FilterSelect } from "@ui/filters/FilterSelect.jsx";

const options = (count, prefix = "Opcion") =>
  Array.from({ length: count }, (_unused, index) => ({
    value: `id-${index}`,
    label: `${prefix} ${index}`,
  }));

describe("FilterSelect", () => {
  test("un catalogo corto se ofrece como desplegable simple", async () => {
    const user = userEvent.setup();
    render(
      <FilterSelect
        emptyLabel="Todos"
        label="Ciclo escolar"
        onChange={vi.fn()}
        options={options(3, "Ciclo")}
        value=""
      />
    );

    await user.click(screen.getByRole("combobox", { name: /Ciclo escolar/ }));

    // La opcion vacia es una fila mas del menu: con tres ciclos es la forma
    // natural de quitar el filtro.
    expect(screen.getByRole("option", { name: "Todos" })).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  test("un catalogo largo se vuelve buscable y filtra al escribir", async () => {
    const user = userEvent.setup();
    render(
      <FilterSelect
        emptyLabel="Todos los estudiantes"
        label="Estudiante"
        onChange={vi.fn()}
        options={[...options(20), { value: "buscado", label: "Zulema Yax" }]}
        value=""
      />
    );

    // Es el caso del historial de matricula: se consulta por persona, y
    // encontrarla entre cientos bajando con la rueda del raton no es buscar.
    const field = screen.getByRole("combobox", { name: /Estudiante/ });
    await user.type(field, "Zulema");

    const matches = screen.getAllByRole("option");
    expect(matches).toHaveLength(1);
    expect(matches[0]).toHaveTextContent("Zulema Yax");
  });

  test("el filtro se quita eligiendo el valor vacio", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <FilterSelect
        emptyLabel="Todos los estudiantes"
        label="Estudiante"
        onChange={onChange}
        options={[...options(20), { value: "buscado", label: "Zulema Yax" }]}
        value="buscado"
      />
    );

    // En la variante buscable la opcion vacia es la "x" de limpiar, que es como
    // se quita un filtro en un buscador.
    await user.click(screen.getByTitle("Todos los estudiantes"));

    expect(onChange).toHaveBeenCalledWith("");
  });
});
