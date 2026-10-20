import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { GuardiansPage } from "@guardians/GuardiansPage.jsx";
import { GuardianStudentsWindow } from "@guardians/GuardianStudentsWindow.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const service = vi.hoisted(() => ({
  list: vi.fn(),
  listPage: vi.fn(),
  linkedStudents: vi.fn(),
  studentCandidates: vi.fn(),
  linkStudent: vi.fn(),
}));
vi.mock("@guardians/guardiansService.js", () => ({
  guardiansService: service,
}));
const guardian = {
  id: 17,
  person: { first_name: "Encargado", last_name: "Sintetico" },
};
const student = {
  public_id: "student-27",
  full_name: "Alumno Sintetico",
  student_code: "G4-027",
};
const relation = {
  id: 21,
  student,
  relationship_label: "Familiar",
  is_primary: true,
  starts_at: "2026-01-01",
  ends_at: null,
  is_active: true,
};
const page = (rows = [], count = rows.length, canLink = true) => ({
  results: rows,
  count,
  actions: { link_student: canLink },
});

async function chooseStudent(user) {
  await user.click(
    await screen.findByRole("button", { name: "Vincular estudiante" })
  );
  const input = screen.getByRole("combobox", { name: /Estudiante/ });
  await user.type(input, "Alumno");
  await user.click(
    await screen.findByRole("option", { name: "Alumno Sintetico · G4-027" })
  );
  await user.type(
    screen.getByLabelText(/Parentesco o responsabilidad/),
    "Familiar"
  );
}

describe("G4 estudiantes del encargado", () => {
  beforeEach(() => {
    service.list.mockReset().mockResolvedValue([guardian]);
    // El listado pide páginas al servidor; `list` sigue siendo la fuente de
    // las filas.
    service.listPage.mockReset().mockImplementation(async () => {
      const results = await service.list();
      return { results, count: results.length, next: null, previous: null };
    });
    service.linkedStudents.mockReset().mockResolvedValue(page());
    service.studentCandidates
      .mockReset()
      .mockResolvedValue({ results: [student], count: 1 });
    service.linkStudent.mockReset().mockResolvedValue(relation);
  });

  test("abre desde el detalle y vuelve sin consultar relaciones antes de pedirlas", async () => {
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);
    await user.click(
      await screen.findByRole("button", { name: /Ver detalle de Encargado/ })
    );
    expect(service.linkedStudents).not.toHaveBeenCalled();
    await user.click(
      screen.getByRole("button", { name: "Estudiantes vinculados" })
    );
    expect(
      await screen.findByText(
        "No hay relaciones con estudiantes dentro de su alcance."
      )
    ).toBeInTheDocument();
    expect(service.linkedStudents).toHaveBeenCalledWith(17, { page: 1 });
    await user.click(
      screen.getByRole("button", { name: "Volver al encargado" })
    );
    expect(
      await screen.findByRole("dialog", { name: "Encargado Sintetico" })
    ).toBeInTheDocument();
    expect(service.studentCandidates).not.toHaveBeenCalled();
  });

  test("pagina las relaciones, conserva historial y enlaza al expediente por UUID", async () => {
    service.linkedStudents.mockImplementation((_id, { page: current }) =>
      Promise.resolve(
        current === 1
          ? page([relation], 26, false)
          : page(
              [
                {
                  ...relation,
                  id: 22,
                  ends_at: "2026-02-01",
                  is_primary: false,
                },
              ],
              26,
              false
            )
      )
    );
    const user = userEvent.setup();
    renderWithRouter(
      <GuardianStudentsWindow guardian={guardian} onClose={vi.fn()} />
    );
    expect(
      await screen.findByRole("link", { name: "Alumno Sintetico · G4-027" })
    ).toHaveAttribute("href", "/app/alumnos/student-27");
    expect(screen.getByText("Familiar · Principal")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Vincular estudiante" })
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    expect(await screen.findByText(/Finalizado/)).toBeInTheDocument();
    expect(service.linkedStudents).toHaveBeenLastCalledWith(17, { page: 2 });
  });

  test("un error de autorización se muestra sin simular una lista vacía y permite reintentar", async () => {
    service.linkedStudents.mockRejectedValueOnce(
      new Error("No tiene permiso para consultar estudiantes.")
    );
    const user = userEvent.setup();
    renderWithRouter(
      <GuardianStudentsWindow guardian={guardian} onClose={vi.fn()} />
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No tiene permiso"
    );
    expect(
      screen.queryByText(
        "No hay relaciones con estudiantes dentro de su alcance."
      )
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Vincular estudiante" })
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(
      await screen.findByText(
        "No hay relaciones con estudiantes dentro de su alcance."
      )
    ).toBeInTheDocument();
  });

  test("busca candidatos solo desde dos letras y cancelar no crea vínculos", async () => {
    const user = userEvent.setup();
    renderWithRouter(
      <GuardianStudentsWindow guardian={guardian} onClose={vi.fn()} />
    );
    await user.click(
      await screen.findByRole("button", { name: "Vincular estudiante" })
    );
    await user.type(screen.getByRole("combobox", { name: /Estudiante/ }), "A");
    expect(service.studentCandidates).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Cancelar vínculo" }));
    expect(service.linkStudent).not.toHaveBeenCalled();
    expect(
      await screen.findByRole("button", { name: "Vincular estudiante" })
    ).toBeInTheDocument();
  });

  test("vincula con UUID, recarga desde página uno y renueva la búsqueda de candidatos", async () => {
    const user = userEvent.setup();
    renderWithRouter(
      <GuardianStudentsWindow guardian={guardian} onClose={vi.fn()} />
    );
    await chooseStudent(user);
    service.linkedStudents.mockResolvedValue(page([relation]));
    await user.click(
      screen.getByRole("button", { name: "Vincular estudiante" })
    );
    expect(
      await screen.findByText("Estudiante vinculado. El historial se conserva.")
    ).toBeInTheDocument();
    expect(service.linkStudent).toHaveBeenCalledExactlyOnceWith(17, {
      student_public_id: "student-27",
      relationship_label: "Familiar",
    });
    expect(
      await screen.findByRole("link", { name: "Alumno Sintetico · G4-027" })
    ).toBeInTheDocument();
    expect(service.linkedStudents).toHaveBeenLastCalledWith(17, { page: 1 });
    service.studentCandidates.mockResolvedValue({ results: [], count: 0 });
    await user.click(
      screen.getByRole("button", { name: "Vincular estudiante" })
    );
    await user.type(
      screen.getByRole("combobox", { name: /Estudiante/ }),
      "Alumno"
    );
    await waitFor(() =>
      expect(service.studentCandidates.mock.calls.length).toBeGreaterThan(1)
    );
    expect(
      screen.queryByRole("option", { name: "Alumno Sintetico · G4-027" })
    ).not.toBeInTheDocument();
  });

  test("conserva selección y parentesco si el permiso cambió antes de guardar", async () => {
    service.linkStudent.mockRejectedValue(
      new Error("El estudiante ya no está en su alcance.")
    );
    const user = userEvent.setup();
    renderWithRouter(
      <GuardianStudentsWindow guardian={guardian} onClose={vi.fn()} />
    );
    await chooseStudent(user);
    await user.click(
      screen.getByRole("button", { name: "Vincular estudiante" })
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "ya no está en su alcance"
    );
    expect(screen.getByLabelText(/Parentesco o responsabilidad/)).toHaveValue(
      "Familiar"
    );
    expect(screen.getByRole("combobox", { name: /Estudiante/ })).toHaveValue(
      "Alumno Sintetico · G4-027"
    );
    expect(service.linkedStudents).toHaveBeenCalledTimes(1);
  });

  test("bloquea doble envío, cierre y paginación durante la escritura", async () => {
    let done;
    service.linkStudent.mockImplementation(
      () =>
        new Promise((resolve) => {
          done = resolve;
        })
    );
    service.linkedStudents.mockResolvedValue(page([relation], 26));
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderWithRouter(
      <GuardianStudentsWindow guardian={guardian} onClose={onClose} />
    );
    await chooseStudent(user);
    await user.dblClick(
      screen.getByRole("button", { name: "Vincular estudiante" })
    );
    expect(
      screen.getByRole("button", { name: "Cancelar vínculo" })
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Volver al encargado" })
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: "Siguiente" })).toBeDisabled();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(onClose).not.toHaveBeenCalled();
    expect(service.linkStudent).toHaveBeenCalledTimes(1);
    done(relation);
    expect(
      await screen.findByText("Estudiante vinculado. El historial se conserva.")
    ).toBeInTheDocument();
  });
});
