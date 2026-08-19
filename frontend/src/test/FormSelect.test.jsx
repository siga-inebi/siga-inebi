import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { FormSelect } from "@ui/forms/FormSelect.jsx";

const options = (count, prefix = "Opcion") =>
  Array.from({ length: count }, (_, index) => ({
    value: `id-${index}`,
    label: `${prefix} ${index}`,
  }));

describe("FormSelect", () => {
  test("un catalogo corto se ofrece como desplegable simple", async () => {
    const user = userEvent.setup();
    render(
      <FormSelect
        label="Jornada"
        onChange={vi.fn()}
        options={options(3)}
        value=""
      />
    );

    await user.click(screen.getByRole("combobox", { name: /Jornada/ }));

    // Sin campo de texto: con tres opciones se leen de un vistazo y escribir
    // seria mas lento que mirar.
    expect(screen.getAllByRole("option")).toHaveLength(3);
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  test("un catalogo largo se vuelve buscable y filtra al escribir", async () => {
    const user = userEvent.setup();
    render(
      <FormSelect
        label="Estudiante"
        onChange={vi.fn()}
        options={[...options(20), { value: "buscado", label: "Zulema Yax" }]}
        value=""
      />
    );

    const field = screen.getByRole("combobox", { name: /Estudiante/ });
    await user.click(field);
    expect(screen.getAllByRole("option")).toHaveLength(21);

    await user.type(field, "Zulema");

    const filtered = screen.getAllByRole("option");
    expect(filtered).toHaveLength(1);
    expect(filtered[0]).toHaveTextContent("Zulema Yax");
  });

  test("el selector buscable emite el valor como un input nativo", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <FormSelect
        label="Estudiante"
        name="student_id"
        onChange={onChange}
        options={[...options(20), { value: "buscado", label: "Zulema Yax" }]}
        value=""
      />
    );

    await user.click(screen.getByRole("combobox", { name: /Estudiante/ }));
    await user.click(screen.getByRole("option", { name: "Zulema Yax" }));

    // El contrato es el del input nativo para que las pantallas no tengan que
    // saber cual de las dos variantes les toco.
    expect(onChange).toHaveBeenCalledWith({
      target: { name: "student_id", value: "buscado" },
    });
  });

  test("etiquetas repetidas no se pierden en el listado", async () => {
    const user = userEvent.setup();
    const repeated = [
      ...options(20),
      { value: "a", label: "Jose Perez" },
      { value: "b", label: "Jose Perez" },
    ];
    render(
      <FormSelect
        label="Encargado"
        onChange={vi.fn()}
        options={repeated}
        value=""
      />
    );

    const field = screen.getByRole("combobox", { name: /Encargado/ });
    await user.click(field);
    await user.type(field, "Jose");

    // Dos personas pueden llamarse igual: si la clave del listado fuera la
    // etiqueta, React descartaria una de las dos filas sin avisar.
    expect(screen.getAllByRole("option")).toHaveLength(2);
  });

  test("mientras el catalogo carga el desplegable lo dice", async () => {
    const user = userEvent.setup();
    render(
      <FormSelect
        label="Ciclo"
        loading
        onChange={vi.fn()}
        options={[]}
        value=""
      />
    );

    await user.click(screen.getByRole("combobox", { name: /Ciclo/ }));

    expect(
      screen.getByRole("option", { name: "Cargando…" })
    ).toBeInTheDocument();
  });
});
