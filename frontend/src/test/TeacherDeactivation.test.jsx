import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, expect, test, vi } from "vitest";

const teachers = vi.hoisted(() => ({
  get: vi.fn(),
  listPositions: vi.fn(),
  deactivate: vi.fn(),
}));
vi.mock("@teachers/teachersService.js", () => ({ teachersService: teachers }));

import { TeacherRecordPage } from "@teachers/TeacherRecordPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const TEACHER = {
  id: 632,
  public_id: "teacher-demo",
  person: {
    first_name: "Docente",
    last_name: "Sintetico",
    email: "docente@example.invalid",
  },
  employee_code: "DOC-DEMO-632",
  specialty: "Especialidad de prueba",
  position: "Docente Titulado",
  is_active: true,
  actions: { deactivate: true },
};

beforeEach(() => {
  teachers.get.mockReset().mockResolvedValue(TEACHER);
  teachers.listPositions
    .mockReset()
    .mockResolvedValue([{ value: TEACHER.position, label: TEACHER.position }]);
  teachers.deactivate.mockReset().mockResolvedValue(null);
});

function renderFicha() {
  return renderWithRouter(
    <Routes>
      <Route
        path="/app/docentes/:teacherId"
        element={<TeacherRecordPage />}
      />
    </Routes>,
    { route: "/app/docentes/632" }
  );
}

async function openConfirmation(user) {
  renderFicha();
  await screen.findByRole("heading", { name: "Docente Sintetico" });
  await user.click(screen.getByRole("button", { name: "Desactivar docente" }));
  return screen.findByRole("dialog", { name: "Desactivar docente" });
}

test("identifica al docente, explica la conservación y cancelar vuelve a su ficha", async () => {
  const user = userEvent.setup();
  const dialog = await openConfirmation(user);
  expect(
    within(dialog).getByText(/Docente Sintetico \(DOC-DEMO-632\)/)
  ).toBeInTheDocument();
  expect(
    within(dialog).getByText(
      /no desactiva su cuenta de acceso ni finaliza asignaciones/
    )
  ).toBeInTheDocument();
  expect(teachers.deactivate).not.toHaveBeenCalled();
  await user.click(within(dialog).getByRole("button", { name: "Cancelar" }));
  expect(
    await screen.findByRole("heading", { name: "Docente Sintetico" })
  ).toBeInTheDocument();
  expect(teachers.deactivate).not.toHaveBeenCalled();
});

test.each([undefined, { deactivate: false }])(
  "sin capacidad del servidor no muestra la acción: %s",
  async (actions) => {
    teachers.get.mockResolvedValue({ ...TEACHER, actions });
    const user = userEvent.setup();
    renderFicha();
    await screen.findByRole("heading", { name: "Docente Sintetico" });
    expect(
      screen.queryByRole("button", { name: "Desactivar docente" })
    ).not.toBeInTheDocument();
  }
);

test("un perfil desactivado conserva su ficha y no permite repetir la baja", async () => {
  teachers.get.mockResolvedValue({
    ...TEACHER,
    is_active: false,
    actions: { deactivate: false },
  });
  const user = userEvent.setup();
  renderFicha();
  await screen.findByRole("heading", { name: "Docente Sintetico" });
  expect(screen.getByText("Desactivado")).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Desactivar docente" })
  ).not.toBeInTheDocument();
});

test("bloquea doble envío, cancelación y Escape mientras procesa", async () => {
  let complete;
  teachers.deactivate.mockImplementation(
    () =>
      new Promise((resolve) => {
        complete = resolve;
      })
  );
  const user = userEvent.setup();
  const dialog = await openConfirmation(user);
  await user.dblClick(
    within(dialog).getByRole("button", { name: "Desactivar docente" })
  );
  expect(teachers.deactivate).toHaveBeenCalledExactlyOnceWith(632);
  expect(
    within(dialog).getByRole("button", { name: "Cancelar" })
  ).toBeDisabled();
  expect(
    within(dialog).getByRole("button", { name: "Desactivar docente" })
  ).toBeDisabled();
  await user.keyboard("{Escape}");
  expect(dialog).toBeInTheDocument();
  await act(async () => complete(null));
  expect(
    await screen.findByText("Docente desactivado. El historial se conserva.")
  ).toBeInTheDocument();
  // La ficha se recarga para reflejar la baja; la vista se conserva en pantalla.
  await waitFor(() => expect(teachers.get).toHaveBeenCalledTimes(2));
  expect(
    screen.getByRole("heading", { name: "Docente Sintetico" })
  ).toBeInTheDocument();
});

test("un rechazo conserva el destino y permite reintentar sin asumir éxito", async () => {
  teachers.deactivate.mockRejectedValueOnce(
    new Error("El permiso ya no está vigente.")
  );
  const user = userEvent.setup();
  const dialog = await openConfirmation(user);
  await user.click(
    within(dialog).getByRole("button", { name: "Desactivar docente" })
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "El permiso ya no está vigente."
  );
  expect(teachers.get).toHaveBeenCalledTimes(1);
  expect(screen.queryByText(/Docente desactivado/)).not.toBeInTheDocument();
  await user.click(
    within(dialog).getByRole("button", { name: "Desactivar docente" })
  );
  expect(
    await screen.findByText("Docente desactivado. El historial se conserva.")
  ).toBeInTheDocument();
  expect(teachers.deactivate.mock.calls).toEqual([[632], [632]]);
});

test("si falla la recarga después del DELETE exitoso reintenta solo la lectura", async () => {
  teachers.get
    .mockResolvedValueOnce(TEACHER)
    .mockRejectedValueOnce(new Error("No se pudo actualizar el listado."));
  const user = userEvent.setup();
  const dialog = await openConfirmation(user);
  await user.click(
    within(dialog).getByRole("button", { name: "Desactivar docente" })
  );
  expect(
    await screen.findByText("Docente desactivado. El historial se conserva.")
  ).toBeInTheDocument();
  expect(
    await screen.findByText("No se pudo actualizar el listado.")
  ).toBeInTheDocument();
  teachers.get.mockResolvedValue(TEACHER);
  await user.click(await screen.findByRole("button", { name: "Reintentar" }));
  await waitFor(() => expect(teachers.get).toHaveBeenCalledTimes(3));
  expect(teachers.deactivate).toHaveBeenCalledTimes(1);
  expect(
    screen.queryByText("No se pudo actualizar el listado.")
  ).not.toBeInTheDocument();
});
