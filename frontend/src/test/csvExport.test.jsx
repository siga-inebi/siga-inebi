import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

const csvMock = vi.hoisted(() => ({ triggerCsvDownload: vi.fn() }));
vi.mock("@shared/utils/csv.js", async (importOriginal) => ({
  ...(await importOriginal()),
  triggerCsvDownload: csvMock.triggerCsvDownload,
}));

import { exportAllToCsv } from "@shared/utils/csvExport.js";
import { ExportCsvButton } from "@ui/buttons/ExportCsvButton.jsx";

import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const COLUMNS = [{ label: "Nombre", value: (row) => row.name }];

function pagedFetch(total, pageSize = 100) {
  return vi.fn(async ({ page }) => {
    const start = (page - 1) * pageSize;
    const size = Math.min(pageSize, total - start);
    return {
      count: total,
      next: start + size < total ? `?page=${page + 1}` : null,
      results: Array.from({ length: size }, (_, i) => ({
        name: `Persona ${start + i + 1}`,
      })),
    };
  });
}

describe("exportacion CSV completa (ux-ui 1.1)", () => {
  beforeEach(() => {
    csvMock.triggerCsvDownload.mockReset();
  });

  test("usa los filtros vigentes y exporta todas las filas, sin tope de 1 000", async () => {
    const fetchPage = pagedFetch(1250);
    const onProgress = vi.fn();

    const exported = await exportAllToCsv({
      fetchPage,
      params: { status: "active" },
      columns: COLUMNS,
      filename: "cuentas.csv",
      onProgress,
    });

    expect(exported).toBe(1250);
    expect(fetchPage).toHaveBeenCalledWith({
      status: "active",
      page: 1,
      page_size: 100,
    });
    expect(fetchPage).toHaveBeenCalledTimes(13);
    const [filename, csv] = csvMock.triggerCsvDownload.mock.calls[0];
    expect(filename).toBe("cuentas.csv");
    expect(csv.split("\r\n")).toHaveLength(1251);
    expect(onProgress).toHaveBeenLastCalledWith({ loaded: 1250, total: 1250 });
  });

  test("el boton muestra el resultado de la exportacion", async () => {
    const user = userEvent.setup();
    renderWithRouter(
      <ExportCsvButton
        columns={COLUMNS}
        fetchPage={pagedFetch(3)}
        filename="lista.csv"
        params={{ search: "ana" }}
      />
    );

    await user.click(screen.getByRole("button", { name: "Exportar CSV" }));

    expect(
      await screen.findByText(/Se exportaron 3 filas/)
    ).toBeInTheDocument();
    expect(csvMock.triggerCsvDownload).toHaveBeenCalledTimes(1);
  });
});
