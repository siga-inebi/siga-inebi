import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Link, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

const teachersServiceMock = vi.hoisted(() => ({
  get: vi.fn(),
  listPositions: vi.fn(),
  update: vi.fn(),
  deactivate: vi.fn(),
}));
vi.mock("@teachers/teachersService.js", () => ({
  teachersService: teachersServiceMock,
}));

const documentsServiceMock = vi.hoisted(() => ({
  listTeacherRecords: vi.fn(),
}));
vi.mock("@documents/documentsService.js", () => ({
  documentsService: documentsServiceMock,
}));

vi.mock("@academics/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});

import { TeacherRecordPage } from "@teachers/TeacherRecordPage.jsx";
import { paginated } from "./fixtures/academics.js";
import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";
import {
  academicsServiceMock,
  resetAcademicsServiceMock,
} from "./mocks/academicsService.js";
import {
  editInstitutionalPerson,
  visibleInstitutionalPerson,
} from "./helpers/institutionalPerson.js";

const TEACHER = {
  id: 1,
  public_id: "teacher-1",
  person: {
    ...visibleInstitutionalPerson,
    public_id: "person-21",
    first_name: "Marvin Estuardo",
    last_name: "Lopez Cifuentes",
    email: "marvin@example.test",
    phone_number: "5566-1234",
  },
  specialty: "Electricidad Industrial",
  position: "Docente Titulado",
  employee_code: "EMP-0142",
  appointment_date: "2019-01-15",
  is_active: true,
  photo: "http://localhost/media/teacher_photos/marvin.png",
  actions: { deactivate: true },
};
const POSITIONS = [
  "Docente Titulado",
  "Docente Interino",
  "Orientador/a",
  "Administrativo",
].map((value) => ({ value, label: value }));
const ASSIGNMENT = {
  public_id: "assign-1",
  section: { public_id: "section-a", name: "A", grade_name: "Primero" },
  subject: { public_id: "subject-mat", name: "Matemática", code: "MAT" },
  teacher: { public_id: "teacher-1", name: "Marvin Estuardo Lopez Cifuentes" },
  starts_on: "2026-01-20",
  ends_on: null,
};

describe("TeacherRecordPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetAcademicsServiceMock();
    teachersServiceMock.get.mockReset().mockResolvedValue(TEACHER);
    teachersServiceMock.listPositions.mockReset().mockResolvedValue(POSITIONS);
    teachersServiceMock.update.mockReset();
    teachersServiceMock.deactivate.mockReset().mockResolvedValue(null);
    documentsServiceMock.listTeacherRecords
      .mockReset()
      .mockResolvedValue(paginated([]));
  });

  test("muestra la ficha con sus datos y consulta Qué imparte solo con permiso", async () => {
    academicsServiceMock.listTeachingAssignments.mockResolvedValue(
      paginated([ASSIGNMENT])
    );
    renderFicha({ permissions: ["scope.assign"] });

    expect(
      await screen.findByRole("heading", {
        name: "Marvin Estuardo Lopez Cifuentes",
      })
    ).toBeInTheDocument();
    expect(teachersServiceMock.get).toHaveBeenCalledWith("1");
    expect(screen.getByText("Electricidad Industrial")).toBeInTheDocument();
    expect(screen.getByText("marvin@example.test")).toBeInTheDocument();
    expect(screen.getByText("15 ene 2019")).toBeInTheDocument();

    const assignments = await screen.findByLabelText("Qué imparte");
    expect(
      await within(assignments).findByText("Matemática")
    ).toBeInTheDocument();
    expect(
      academicsServiceMock.listTeachingAssignments
    ).toHaveBeenCalledWith({ teacher_id: "teacher-1", current: true });

    // Las lecturas a demanda no se adelantan: el expediente se pide al abrirlo.
    expect(documentsServiceMock.listTeacherRecords).not.toHaveBeenCalled();
  });

  test("sin permiso de asignaciones no consulta ni muestra Qué imparte", async () => {
    renderFicha();
    await screen.findByRole("heading", {
      name: "Marvin Estuardo Lopez Cifuentes",
    });
    expect(screen.queryByLabelText("Qué imparte")).not.toBeInTheDocument();
    expect(
      academicsServiceMock.listTeachingAssignments
    ).not.toHaveBeenCalled();
  });

  test("carga el expediente documental únicamente al solicitarlo", async () => {
    const user = userEvent.setup();
    renderFicha();
    await screen.findByRole("heading", {
      name: "Marvin Estuardo Lopez Cifuentes",
    });
    expect(documentsServiceMock.listTeacherRecords).not.toHaveBeenCalled();

    await user.click(
      screen.getByRole("button", { name: "Documentos", exact: true })
    );
    expect(
      await screen.findByRole("heading", {
        name: "Expediente documental del docente",
      })
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(documentsServiceMock.listTeacherRecords).toHaveBeenCalledWith(
        "teacher-1",
        expect.objectContaining({ page: 1 })
      )
    );
  });

  test("abre y cierra el lightbox de foto", async () => {
    const user = userEvent.setup();
    renderFicha();
    await screen.findByRole("heading", {
      name: "Marvin Estuardo Lopez Cifuentes",
    });

    await user.click(
      screen.getByAltText("Foto de Marvin Estuardo Lopez Cifuentes")
    );
    const lightbox = await screen.findByRole("dialog", {
      name: "Foto de Marvin Estuardo Lopez Cifuentes",
    });
    const downloadLink = within(lightbox).getByRole("link", {
      name: "Descargar",
    });
    expect(downloadLink).toHaveAttribute(
      "href",
      "http://localhost/media/teacher_photos/marvin.png"
    );
    expect(downloadLink).toHaveAttribute("download", "marvin.png");

    await user.click(
      within(lightbox).getByRole("button", { name: "Cerrar imagen" })
    );
    // El dialogo se desmonta al terminar su animacion de salida, no en el clic.
    await waitFor(() =>
      expect(
        screen.queryByRole("dialog", {
          name: "Foto de Marvin Estuardo Lopez Cifuentes",
        })
      ).not.toBeInTheDocument()
    );
  });

  test("edita desde la ficha y actualiza los datos sin recargar la pagina", async () => {
    teachersServiceMock.update.mockResolvedValue({
      ...TEACHER,
      person: { ...TEACHER.person, last_name: "Lopez Mendez" },
    });
    const user = userEvent.setup();
    renderFicha();
    await screen.findByRole("heading", {
      name: "Marvin Estuardo Lopez Cifuentes",
    });

    await user.click(screen.getByRole("button", { name: "Editar" }));
    // CUI y fecha de nacimiento no se corrigen despues del alta.
    expect(screen.queryByLabelText(/^CUI/)).not.toBeInTheDocument();
    expect(
      screen.queryByLabelText(/^Fecha de nacimiento/)
    ).not.toBeInTheDocument();

    const lastNameInput = screen.getByLabelText(/^Apellidos/);
    expect(lastNameInput).toHaveValue("Lopez Cifuentes");
    await user.clear(lastNameInput);
    await user.type(lastNameInput, "Lopez Mendez");
    await editInstitutionalPerson(user);
    await user.click(screen.getByRole("button", { name: "Guardar cambios" }));

    await waitFor(() =>
      expect(teachersServiceMock.update).toHaveBeenCalledTimes(1)
    );
    expect(teachersServiceMock.update).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        person: expect.objectContaining({
          public_id: "person-21",
          first_name: "Marvin Estuardo",
          last_name: "Lopez Mendez",
          email: "marvin@example.test",
          phone_number: "5566-1234",
        }),
        specialty: "Electricidad Industrial",
        position: "Docente Titulado",
        employee_code: "EMP-0142",
      })
    );
    expect(
      await screen.findByRole("heading", { name: "Marvin Estuardo Lopez Mendez" })
    ).toBeInTheDocument();
    expect(screen.getByText("Cambios guardados.")).toBeInTheDocument();
  });

  test("volver conserva los filtros del listado de origen", async () => {
    const user = userEvent.setup();
    renderWithSession(
      <Routes>
        <Route
          path="/app/docentes"
          element={
            <Link
              to="/app/docentes/1"
              state={{
                teacherListLocation: "/app/docentes?position=Docente+Titulado",
              }}
            >
              Abrir ficha
            </Link>
          }
        />
        <Route
          path="/app/docentes/:teacherId"
          element={<TeacherRecordPage />}
        />
      </Routes>,
      { route: "/app/docentes", user: sessionUser([]) }
    );
    await user.click(screen.getByRole("link", { name: "Abrir ficha" }));
    await screen.findByRole("heading", {
      name: "Marvin Estuardo Lopez Cifuentes",
    });

    expect(screen.getByRole("link", { name: "Volver a docentes" })).toHaveAttribute(
      "href",
      "/app/docentes?position=Docente+Titulado"
    );
  });
});

function renderFicha({ route = "/app/docentes/1", permissions = [] } = {}) {
  return renderWithSession(
    <Routes>
      <Route
        path="/app/docentes/:teacherId"
        element={<TeacherRecordPage />}
      />
      <Route path="/app/docentes" element={<p>Listado de docentes</p>} />
    </Routes>,
    { route, user: sessionUser(permissions) }
  );
}
