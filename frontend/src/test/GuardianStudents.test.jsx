import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { GuardiansPage } from "@guardians/GuardiansPage.jsx";
import { GuardianStudentsSection } from "@guardians/GuardianStudentsSection.jsx";
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
const students = vi.hoisted(() => ({
  endGuardianRelation: vi.fn(),
  listRecordGuardians: vi.fn(),
}));
vi.mock("@students/studentsService.js", () => ({ studentsService: students }));

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
  is_primary: false,
  starts_at: "2026-01-01",
  ends_at: null,
  is_active: true,
  actions: { end: true, offers_replacement: false },
};
const page = (rows = [], count = rows.length, canLink = true) => ({
  results: rows,
  count,
  actions: { link_student: canLink },
});

async function chooseStudent(user) {
  await user.click(
    await screen.findByRole("button", { name: "Agregar estudiante" })
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
    students.endGuardianRelation.mockReset().mockResolvedValue({});
    students.listRecordGuardians.mockReset();
  });

  test("la ficha muestra datos y estudiantes en una sola ventana", async () => {
    const user = userEvent.setup();
    renderWithRouter(<GuardiansPage />);
    expect(service.linkedStudents).not.toHaveBeenCalled();
    await user.click(
      await screen.findByRole("button", { name: /Ver detalle de Encargado/ })
    );
    const detail = await screen.findByRole("dialog", {
      name: "Encargado Sintetico",
    });
    expect(
      await within(detail).findByText(
        "No hay relaciones con estudiantes dentro de su alcance."
      )
    ).toBeInTheDocument();
    expect(within(detail).getByText("Nombre completo")).toBeInTheDocument();
    expect(screen.getAllByRole("dialog")).toHaveLength(1);
    expect(service.linkedStudents).toHaveBeenCalledWith(17, { page: 1 });
    expect(service.studentCandidates).not.toHaveBeenCalled();
  });

  test("muestra las relaciones como tabla, pagina y enlaza al expediente por UUID", async () => {
    service.linkedStudents.mockImplementation((_id, { page: current }) =>
      Promise.resolve(
        current === 1
          ? page([{ ...relation, is_primary: true }], 26, false)
          : page(
              [
                {
                  ...relation,
                  id: 22,
                  ends_at: "2026-02-01",
                  actions: { end: false, offers_replacement: false },
                },
              ],
              26,
              false
            )
      )
    );
    const user = userEvent.setup();
    renderWithRouter(<GuardianStudentsSection guardian={guardian} />);
    const link = await screen.findByRole("link", {
      name: "Alumno Sintetico · G4-027",
    });
    expect(link).toHaveAttribute("href", "/app/alumnos/student-27");
    const row = link.closest("tr");
    expect(within(row).getByText("Familiar")).toBeInTheDocument();
    expect(within(row).getByText("Principal")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Agregar estudiante" })
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    expect(await screen.findByText(/Finalizado/)).toBeInTheDocument();
    expect(service.linkedStudents).toHaveBeenLastCalledWith(17, { page: 2 });
    expect(
      screen.queryByRole("button", { name: /Quitar vínculo/ })
    ).not.toBeInTheDocument();
  });

  test("un error de autorización se muestra sin simular una lista vacía y permite reintentar", async () => {
    service.linkedStudents.mockRejectedValueOnce(
      new Error("No tiene permiso para consultar estudiantes.")
    );
    const user = userEvent.setup();
    renderWithRouter(<GuardianStudentsSection guardian={guardian} />);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No tiene permiso"
    );
    expect(
      screen.queryByText(
        "No hay relaciones con estudiantes dentro de su alcance."
      )
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Agregar estudiante" })
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
    renderWithRouter(<GuardianStudentsSection guardian={guardian} />);
    await user.click(
      await screen.findByRole("button", { name: "Agregar estudiante" })
    );
    await user.type(screen.getByRole("combobox", { name: /Estudiante/ }), "A");
    expect(service.studentCandidates).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Cancelar vínculo" }));
    expect(service.linkStudent).not.toHaveBeenCalled();
    expect(
      await screen.findByRole("button", { name: "Agregar estudiante" })
    ).toBeInTheDocument();
  });

  test("vincula con UUID, recarga desde página uno y renueva la búsqueda de candidatos", async () => {
    const user = userEvent.setup();
    renderWithRouter(<GuardianStudentsSection guardian={guardian} />);
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
      screen.getByRole("button", { name: "Agregar estudiante" })
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
    renderWithRouter(<GuardianStudentsSection guardian={guardian} />);
    await chooseStudent(user);
    await user.click(
      screen.getByRole("button", { name: "Vincular estudiante" })
    );
    expect(await screen.findByText(/ya no está en su alcance/)).toBeVisible();
    expect(screen.getByLabelText(/Parentesco o responsabilidad/)).toHaveValue(
      "Familiar"
    );
    expect(screen.getByRole("combobox", { name: /Estudiante/ })).toHaveValue(
      "Alumno Sintetico · G4-027"
    );
    expect(service.linkedStudents).toHaveBeenCalledTimes(1);
  });

  test("bloquea doble envío y avisa a la ficha durante la escritura", async () => {
    let done;
    service.linkStudent.mockImplementation(
      () =>
        new Promise((resolve) => {
          done = resolve;
        })
    );
    service.linkedStudents.mockResolvedValue(page([relation], 26));
    const onBusy = vi.fn();
    const user = userEvent.setup();
    renderWithRouter(
      <GuardianStudentsSection guardian={guardian} onBusy={onBusy} />
    );
    await chooseStudent(user);
    await user.dblClick(
      screen.getByRole("button", { name: "Vincular estudiante" })
    );
    expect(
      screen.getByRole("button", { name: "Cancelar vínculo" })
    ).toBeDisabled();
    expect(onBusy).toHaveBeenLastCalledWith(true);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(service.linkStudent).toHaveBeenCalledTimes(1);
    done(relation);
    expect(
      await screen.findByText("Estudiante vinculado. El historial se conserva.")
    ).toBeInTheDocument();
    expect(onBusy).toHaveBeenLastCalledWith(false);
  });

  test("quitar un vínculo secundario lo finaliza sin pedir reemplazo", async () => {
    service.linkedStudents.mockResolvedValue(page([relation]));
    const user = userEvent.setup();
    renderWithRouter(<GuardianStudentsSection guardian={guardian} />);
    await user.click(
      await screen.findByRole("button", {
        name: "Quitar vínculo con Alumno Sintetico",
      })
    );
    const panel = screen.getByLabelText("Quitar vínculo");
    expect(within(panel).getByText(/historial se conservará/)).toBeVisible();
    await user.click(within(panel).getByRole("button", { name: "Cancelar" }));
    expect(students.endGuardianRelation).not.toHaveBeenCalled();
    await user.click(
      screen.getByRole("button", {
        name: "Quitar vínculo con Alumno Sintetico",
      })
    );
    await user.click(
      within(screen.getByLabelText("Quitar vínculo")).getByRole("button", {
        name: "Quitar vínculo",
      })
    );
    expect(
      await screen.findByText("Vínculo finalizado. El historial se conserva.")
    ).toBeInTheDocument();
    expect(students.endGuardianRelation).toHaveBeenCalledExactlyOnceWith(
      21,
      {}
    );
    expect(service.linkedStudents).toHaveBeenLastCalledWith(17, { page: 1 });
  });

  test("quitar el vínculo principal pide elegir el nuevo principal", async () => {
    service.linkedStudents.mockResolvedValue(
      page([
        {
          ...relation,
          is_primary: true,
          actions: { end: true, offers_replacement: true },
        },
      ])
    );
    students.listRecordGuardians.mockResolvedValue({
      results: [
        {
          id: 33,
          relationship_label: "Madre",
          guardian_detail: { person: { first_name: "Ana", last_name: "Demo" } },
        },
      ],
      count: 1,
    });
    const user = userEvent.setup();
    renderWithRouter(<GuardianStudentsSection guardian={guardian} />);
    await user.click(
      await screen.findByRole("button", {
        name: "Quitar vínculo con Alumno Sintetico",
      })
    );
    await user.click(
      await screen.findByRole("button", { name: "Elegir Ana Demo · Madre" })
    );
    expect(students.listRecordGuardians).toHaveBeenCalledWith("student-27", {
      page: 1,
      replacement_for: 21,
    });
    expect(screen.getByText(/Nuevo principal: Ana Demo/)).toBeVisible();
    await user.click(
      within(screen.getByLabelText("Quitar vínculo")).getByRole("button", {
        name: "Quitar vínculo",
      })
    );
    await waitFor(() =>
      expect(students.endGuardianRelation).toHaveBeenCalledExactlyOnceWith(21, {
        replacement_relation: 33,
      })
    );
  });

  test("quitar el principal sin otro encargado lo deja sin principal", async () => {
    service.linkedStudents.mockResolvedValue(
      page([
        {
          ...relation,
          is_primary: true,
          actions: { end: true, offers_replacement: true },
        },
      ])
    );
    students.listRecordGuardians.mockResolvedValue({ results: [], count: 0 });
    const user = userEvent.setup();
    renderWithRouter(<GuardianStudentsSection guardian={guardian} />);
    expect(
      await screen.findByRole("columnheader", { name: "Rol del encargado" })
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", {
        name: "Quitar vínculo con Alumno Sintetico",
      })
    );
    await screen.findByText("No hay otros vínculos vigentes para elegir.");
    await user.click(
      screen.getByRole("button", { name: "Continuar sin nuevo principal" })
    );
    const panel = screen.getByLabelText("Quitar vínculo");
    expect(
      within(panel).getByText(/quedará sin encargado principal/)
    ).toBeVisible();
    await user.click(
      within(panel).getByRole("button", { name: "Quitar vínculo" })
    );
    await waitFor(() =>
      expect(students.endGuardianRelation).toHaveBeenCalledExactlyOnceWith(
        21,
        {}
      )
    );
  });
});
