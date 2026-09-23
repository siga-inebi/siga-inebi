import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

vi.mock("@academics/academicsService.js", () => ({
  PAGE_SIZE: 25,
  academicsService: {
    listClassrooms: vi.fn(),
    listCampuses: vi.fn(),
    updateClassroom: vi.fn(),
  },
}));

import { academicsService } from "@academics/academicsService.js";
import { RoomsPage } from "@academics/RoomsPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const room = {
  public_id: "room-demo",
  name: "Aula demo",
  code: "A-1",
  location: "Edificio demo",
  capacity: 30,
  is_active: true,
  service_status: "available",
  campus: { public_id: "campus-demo", name: "Sede demo" },
};
const page = (rows) => ({ count: rows.length, results: rows, next: null });

beforeEach(() => {
  vi.resetAllMocks();
  academicsService.listClassrooms.mockResolvedValue(page([room]));
  academicsService.listCampuses.mockResolvedValue(page([room.campus]));
  academicsService.updateClassroom.mockResolvedValue({
    ...room,
    service_status: "maintenance",
  });
});

test("cambia disponibilidad, explica la conservacion y muestra el estado guardado", async () => {
  const user = userEvent.setup();
  renderWithRouter(<RoomsPage />);
  expect(await screen.findByText("Disponible")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Editar" }));
  expect(
    screen.getByText(/Las sesiones existentes se conservan/)
  ).toBeInTheDocument();
  await user.click(screen.getByRole("combobox", { name: /Disponibilidad/ }));
  await user.click(screen.getByRole("option", { name: "En mantenimiento" }));
  academicsService.listClassrooms.mockResolvedValue(
    page([{ ...room, service_status: "maintenance" }])
  );
  await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
  await waitFor(() =>
    expect(academicsService.updateClassroom).toHaveBeenCalledWith(
      room.public_id,
      expect.objectContaining({ service_status: "maintenance" })
    )
  );
  expect(await screen.findByText("En mantenimiento")).toBeInTheDocument();
});

test("un error al guardar mantiene el formulario y el estado de la lista", async () => {
  const user = userEvent.setup();
  academicsService.updateClassroom.mockRejectedValue(
    new Error("No se pudo guardar")
  );
  renderWithRouter(<RoomsPage />);
  await user.click(await screen.findByRole("button", { name: "Editar" }));
  await user.click(screen.getByRole("combobox", { name: /Disponibilidad/ }));
  await user.click(
    screen.getByRole("option", { name: "Temporalmente inhabilitada" })
  );
  await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
  expect(await screen.findByText("No se pudo guardar")).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Guardar cambios" })
  ).toBeInTheDocument();
  expect(screen.getByText("Disponible")).toBeInTheDocument();
});
