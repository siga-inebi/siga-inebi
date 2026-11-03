import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { DataTable } from "@ui/table/DataTable.jsx";

import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const COLUMNS = [{ key: "name", label: "Nombre" }];
const ROWS = [{ id: 1, name: "Ana" }];

describe("DataTable: Filas por página (ux-ui 1.1.1)", () => {
  test("no muestra el selector cuando la pantalla no lo atiende", () => {
    renderWithRouter(
      <DataTable
        columns={COLUMNS}
        pagination={{
          page: 0,
          rowsPerPage: 25,
          total: 60,
          onPageChange: vi.fn(),
        }}
        rows={ROWS}
      />
    );

    expect(screen.queryByText("Filas por página:")).not.toBeInTheDocument();
    expect(screen.getByText("Mostrando 1–25 de 60")).toBeInTheDocument();
  });

  test("muestra el selector y avisa el tamano elegido cuando hay manejador", async () => {
    const user = userEvent.setup();
    const onRowsPerPageChange = vi.fn();
    renderWithRouter(
      <DataTable
        columns={COLUMNS}
        pagination={{
          page: 0,
          rowsPerPage: 25,
          total: 60,
          onPageChange: vi.fn(),
          onRowsPerPageChange,
        }}
        rows={ROWS}
      />
    );

    expect(screen.getByText("Filas por página:")).toBeInTheDocument();
    await user.click(screen.getByRole("combobox"));
    await user.click(
      within(await screen.findByRole("listbox")).getByRole("option", {
        name: "50",
      })
    );

    expect(onRowsPerPageChange).toHaveBeenCalledWith(50);
  });

  test("los botones de pagina tienen nombre accesible en español", () => {
    renderWithRouter(
      <DataTable
        columns={COLUMNS}
        pagination={{
          page: 0,
          rowsPerPage: 25,
          total: 60,
          onPageChange: vi.fn(),
        }}
        rows={ROWS}
      />
    );

    expect(
      screen.getByRole("button", { name: "Siguiente" })
    ).toBeInTheDocument();
  });
});

describe("DataTable: selección de filas", () => {
  const SELECT_ROWS = [
    { id: 1, name: "Ana" },
    { id: 2, name: "Beto" },
  ];

  test("sin `selectable` no muestra casillas", () => {
    renderWithRouter(<DataTable columns={COLUMNS} rows={SELECT_ROWS} />);
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  test("marca una fila sin abrirla y conserva lo elegido en otras páginas", async () => {
    const user = userEvent.setup();
    const onSelectionChange = vi.fn();
    const onRowClick = vi.fn();
    renderWithRouter(
      <DataTable
        columns={COLUMNS}
        getRowLabel={(row) => `Seleccionar a ${row.name}`}
        onRowClick={onRowClick}
        onSelectionChange={onSelectionChange}
        rows={SELECT_ROWS}
        selectable
        selectedIds={[99]}
      />
    );

    await user.click(
      screen.getByRole("checkbox", { name: "Seleccionar a Ana" })
    );
    expect(onSelectionChange).toHaveBeenLastCalledWith([99, 1]);
    expect(onRowClick).not.toHaveBeenCalled();

    await user.click(
      screen.getByRole("checkbox", {
        name: "Seleccionar las filas de esta página",
      })
    );
    expect(onSelectionChange).toHaveBeenLastCalledWith([99, 1, 2]);
  });

  test("la casilla de cabecera desmarca solo la página visible", async () => {
    const user = userEvent.setup();
    const onSelectionChange = vi.fn();
    renderWithRouter(
      <DataTable
        columns={COLUMNS}
        onSelectionChange={onSelectionChange}
        rows={SELECT_ROWS}
        selectable
        selectedIds={[1, 99, 2]}
      />
    );

    const header = screen.getByRole("checkbox", {
      name: "Seleccionar las filas de esta página",
    });
    expect(header).toBeChecked();
    await user.click(header);
    expect(onSelectionChange).toHaveBeenLastCalledWith([99]);
  });
});
