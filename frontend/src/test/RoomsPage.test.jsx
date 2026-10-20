import { fireEvent, screen, waitFor } from "@testing-library/react";
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
import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";

function renderWithRouter(ui, permissions = ["scope.assign"]) {
  return renderWithSession(ui, { user: sessionUser(permissions) });
}

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

test("pide una sola página de sedes para el filtro y filtra en el servidor", async () => {
  const user = userEvent.setup();
  renderWithRouter(<RoomsPage />);
  expect(await screen.findByText("Aula demo")).toBeInTheDocument();
  expect(academicsService.listClassrooms).toHaveBeenCalledWith({
    page: 1,
    page_size: 25,
    ordering: "name",
  });
  expect(academicsService.listCampuses).toHaveBeenCalledTimes(1);
  expect(academicsService.listCampuses).toHaveBeenCalledWith({
    page: 1,
    page_size: 100,
  });

  await user.click(screen.getByRole("combobox", { name: /^Sede/ }));
  await user.click(await screen.findByRole("option", { name: "Sede demo" }));
  await waitFor(() =>
    expect(academicsService.listClassrooms).toHaveBeenLastCalledWith({
      page: 1,
      page_size: 25,
      ordering: "name",
      campus_id: "campus-demo",
    })
  );

  fireEvent.change(screen.getByPlaceholderText("Buscar por nombre o código"), {
    target: { value: "lab" },
  });
  await waitFor(() =>
    expect(academicsService.listClassrooms).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: "lab", campus_id: "campus-demo" })
    )
  );
});

test("muestra las desactivadas al pedirlo", async () => {
  const user = userEvent.setup();
  renderWithRouter(<RoomsPage />);
  await screen.findByText("Aula demo");
  await user.click(screen.getByLabelText(/^Mostrar desactivados/));
  await waitFor(() =>
    expect(academicsService.listClassrooms).toHaveBeenLastCalledWith(
      expect.objectContaining({ include_inactive: true })
    )
  );
});

test("sin scope.assign no ofrece alta, edición ni baja", async () => {
  renderWithRouter(<RoomsPage />, []);
  expect(await screen.findByText("Aula demo")).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Nueva aula" })
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Editar" })
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Desactivar" })
  ).not.toBeInTheDocument();
});
