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
