import { screen } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";

const storageConsumption = vi.hoisted(() => vi.fn());

vi.mock("@documents/documentsService.js", () => ({
  documentsService: { storageConsumption },
}));

import { DocumentStoragePage } from "@documents/DocumentStoragePage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

beforeEach(() => storageConsumption.mockReset());

test("muestra consumo, proyección, umbral y desglose documental", async () => {
  storageConsumption.mockResolvedValue({
    total_bytes: 1048576,
    file_count: 12,
    retained_count: 3,
    projected_total_bytes: 3221225472,
    warning_threshold_bytes: 2147483648,
    threshold_utilization_percent: 50,
    warning_active: false,
    by_content_type: [
      { content_type: "application/pdf", count: 8, size: 1048576 },
    ],
  });

  renderWithRouter(<DocumentStoragePage />);

  expect(await screen.findAllByText("1.0 MB")).toHaveLength(2);
  expect(screen.getByText("12")).toBeInTheDocument();
  expect(screen.getByText("3")).toBeInTheDocument();
  expect(screen.getByText("application/pdf")).toBeInTheDocument();
  expect(
    screen.getByRole("progressbar", {
      name: "Uso del umbral de almacenamiento",
    })
  ).toHaveAttribute("aria-valuenow", "50");
});
