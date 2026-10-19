import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Link, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

const students = vi.hoisted(() => ({
  getRecord: vi.fn(),
  getRecordStatus: vi.fn(),
  changeRecordStatus: vi.fn(),
  linkRecordGuardian: vi.fn(),
  update: vi.fn(),
  deactivate: vi.fn(),
  listRecordGuardians: vi.fn(),
  listHealthNotesPage: vi.fn(),
  listObservationsPage: vi.fn(),
  listEmergencyContactsPage: vi.fn(),
  createHealthNote: vi.fn(),
  createObservation: vi.fn(),
  createEmergencyContact: vi.fn(),
  createGuardianRelation: vi.fn(),
}));
const guardians = vi.hoisted(() => ({ listPage: vi.fn() }));
const enrolments = vi.hoisted(() => ({ listStudentRecord: vi.fn() }));
const documents = vi.hoisted(() => ({
  listStudentRecords: vi.fn(),
  issueDownloadToken: vi.fn(),
}));
const attendance = vi.hoisted(() => ({ listEvents: vi.fn() }));
vi.mock("@students/studentsService.js", () => ({ studentsService: students }));
vi.mock("@guardians/guardiansService.js", () => ({
  guardiansService: guardians,
}));
vi.mock("@enrolments/enrolmentsService.js", () => ({
  enrolmentsService: enrolments,
  ENROLMENT_STATUS_LABEL: { active: "Activa", completed: "Completada" },
}));
vi.mock("@documents/documentsService.js", () => ({
  documentsService: documents,
}));
vi.mock("@attendance/attendanceService.js", () => ({
  attendanceService: attendance,
  MOVEMENT_LABEL: { entry: "Entrada" },
  ORIGIN_LABEL: { manual: "Manual" },
}));

import { StudentRecordPage } from "@students/StudentRecordPage.jsx";
import { renderWithRouter } from "./helpers/renderWithRouter.jsx";
import {
  visibleInstitutionalPerson,
  editInstitutionalPerson,
  editedInstitutionalPerson,
} from "./helpers/institutionalPerson.js";

const RECORD = {
  id: 1,
  public_id: "student-1",
  student_code: "EST-DEMO",
  status: "active",
  photo: "",
  person: {
    ...visibleInstitutionalPerson,
    public_id: "person-1",
    first_name: "Alumno",
    last_name: "Demo",
    email: "demo@example.invalid",
  },
};
const paged = (results = [], count = results.length) => ({ results, count });
const note = {
  public_id: "note-1",
  content: "Nota de salud demo",
  author: "admin",
  recorded_on: "2026-02-01",
};
beforeEach(() => {
  for (const group of [students, guardians, enrolments, documents, attendance])
    for (const mock of Object.values(group))
      mock.mockReset().mockResolvedValue(paged());
  students.getRecord.mockResolvedValue({
    ...RECORD,
    actions: { link_guardian: true },
  });
  students.update.mockResolvedValue(RECORD);
});
afterEach(() => vi.restoreAllMocks());

test("cambiar estado recarga capacidades y no repite POST si falla esa lectura", async () => {
  const statusContext = {
    status: "active",
    can_change: true,
    last_change: null,
    warnings: [],
    options: [
      { value: "active", label: "Activo" },
      { value: "withdrawn", label: "Retirado" },
    ],
  };
  students.getRecord
    .mockResolvedValueOnce({ ...RECORD, actions: { link_guardian: true } })
    .mockRejectedValueOnce(new Error("No se pudo recargar la ficha"))
    .mockResolvedValue({
      ...RECORD,
      status: "withdrawn",
      actions: { link_guardian: false },
    });
  students.getRecordStatus.mockResolvedValue(statusContext);
  students.changeRecordStatus.mockResolvedValue({
    ...statusContext,
    status: "withdrawn",
  });
  const user = userEvent.setup();
  renderRecord();
  await user.click(
    await screen.findByRole("button", { name: "Cambiar estado" })
  );
  await user.click(screen.getByLabelText("Nuevo estado"));
  await user.click(screen.getByRole("option", { name: "Retirado" }));
  await user.click(screen.getByRole("button", { name: "Revisar cambio" }));
  await user.click(
    await screen.findByRole("button", { name: "Confirmar cambio" })
  );
  await screen.findByText("No se pudo recargar la ficha");
  expect(
    screen.getByText("Estado del expediente actualizado.")
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Reintentar" }));
  await screen.findByText("Retirado");
  expect(students.changeRecordStatus).toHaveBeenCalledOnce();
  await openTab(user, "Encargados");
  await screen.findByText("Sin encargados vinculados");
  expect(
    screen.queryByRole("button", { name: "Vincular encargado" })
  ).not.toBeInTheDocument();
});

function renderRecord(route = "/app/alumnos/student-1") {
  return renderWithRouter(
    <>
      <Link to="/app/alumnos/student-2">Otro estudiante</Link>
      <Routes>
        <Route path="/app/alumnos/:studentId" element={<StudentRecordPage />} />
        <Route path="/app/alumnos" element={<p>Listado de estudiantes</p>} />
      </Routes>
    </>,
    { route }
  );
}
async function openTab(user, name) {
  await user.click(screen.getByRole("tab", { name, exact: true }));
}

test("muestra datos institucionales y ocho pestañas sin lecturas sensibles anticipadas", async () => {
  renderRecord();
  expect(
    await screen.findByRole("heading", { name: "Alumno Demo" })
  ).toBeInTheDocument();
  expect(screen.getAllByRole("tab")).toHaveLength(8);
  for (const value of [
    RECORD.person.address,
    RECORD.person.nationality,
    RECORD.person.department,
    RECORD.person.municipality,
  ])
    expect(screen.getAllByText(value).length).toBeGreaterThan(0);
  expect(students.getRecord).toHaveBeenCalledWith("student-1");
  expect(students.listHealthNotesPage).not.toHaveBeenCalled();
  expect(students.listRecordGuardians).not.toHaveBeenCalled();
  expect(documents.listStudentRecords).not.toHaveBeenCalled();
  expect(attendance.listEvents).not.toHaveBeenCalled();
  expect(screen.queryByText("CUI")).not.toBeInTheDocument();
});

test("presenta el sexo no especificado con una etiqueta en español", async () => {
  students.getRecord.mockResolvedValue({
    ...RECORD,
    person: { ...RECORD.person, sex: "not_specified" },
  });
  renderRecord();
  expect(await screen.findByText("No especificado")).toBeInTheDocument();
  expect(screen.queryByText("not_specified")).not.toBeInTheDocument();
});

test.each([
  [
    "/app/alumnos?page=3&page_size=50&search=DEMO&status=active",
    "/app/alumnos?page=3&page_size=50&search=DEMO&status=active",
  ],
  ["https://example.invalid/otra", "/app/alumnos"],
  ["/app/alumnos/student-2", "/app/alumnos"],
])(
  "volver al listado conserva únicamente un destino de listado válido: %s",
  async (destination, expected) => {
    const user = userEvent.setup();
    renderWithRouter(
      <>
        <Link
          to="/app/alumnos/student-1"
          state={{ studentListLocation: destination }}
        >
          Abrir expediente
        </Link>
        <Routes>
          <Route path="/app/alumnos" element={null} />
          <Route
            path="/app/alumnos/:studentId"
            element={<StudentRecordPage />}
          />
        </Routes>
      </>,
      { route: "/app/alumnos" }
    );
    await user.click(screen.getByRole("link", { name: "Abrir expediente" }));
    await screen.findByRole("heading", { name: "Alumno Demo" });
    expect(screen.getByRole("link", { name: /Volver/ })).toHaveAttribute(
      "href",
      expected
    );
    await openTab(user, "Salud");
    expect(screen.getByRole("link", { name: /Volver/ })).toHaveAttribute(
      "href",
      expected
    );
  }
);

test("conserva borrador y página al cambiar pestañas, sin nuevas lecturas al volver", async () => {
  students.listHealthNotesPage.mockImplementation(async (_id, params) =>
    paged(
      [
        {
          ...note,
          public_id: `note-${params.page}`,
          content: `Nota pagina ${params.page}`,
        },
      ],
      26
    )
  );
  const user = userEvent.setup();
  renderRecord();
  await screen.findByRole("tab", { name: "Salud" });
  await openTab(user, "Salud");
  await screen.findByText("Nota pagina 1");
  await user.click(screen.getByRole("button", { name: "Siguiente" }));
  await screen.findByText("Nota pagina 2");
  await user.click(screen.getByRole("button", { name: "Nueva nota de salud" }));
  await user.type(
    screen.getByLabelText(/Información de salud/),
    "Borrador demo"
  );
  await openTab(user, "Datos");
  await openTab(user, "Salud");
  expect(screen.getByLabelText(/Información de salud/)).toHaveValue(
    "Borrador demo"
  );
  expect(screen.getByText("Nota pagina 2")).toBeInTheDocument();
  expect(students.listHealthNotesPage).toHaveBeenCalledTimes(2);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("crea salud en línea, conserva datos tras error y vuelve a primera página al guardar", async () => {
  students.listHealthNotesPage.mockResolvedValue(paged([note], 26));
  students.createHealthNote.mockRejectedValueOnce(
    new Error("No se pudo guardar")
  );
  students.createHealthNote.mockResolvedValueOnce({
    ...note,
    content: "Nota nueva",
  });
  const user = userEvent.setup();
  renderRecord("/app/alumnos/student-1?tab=health");
  await screen.findByText(note.content);
  await user.click(screen.getByRole("button", { name: "Siguiente" }));
  await waitFor(() =>
    expect(screen.getByText(/Página 2 de 2/)).toBeInTheDocument()
  );
  await user.click(screen.getByRole("button", { name: "Nueva nota de salud" }));
  await user.type(screen.getByLabelText(/Información de salud/), "Nota nueva");
  await user.click(screen.getByRole("button", { name: "Registrar nota" }));
  await screen.findByText("No se pudo guardar");
  expect(screen.getByLabelText(/Información de salud/)).toHaveValue(
    "Nota nueva"
  );
  await user.click(screen.getByRole("button", { name: "Registrar nota" }));
  await waitFor(() =>
    expect(students.createHealthNote).toHaveBeenCalledTimes(2)
  );
  await waitFor(() =>
    expect(students.listHealthNotesPage).toHaveBeenLastCalledWith(
      "student-1",
      expect.objectContaining({ page: 1 })
    )
  );
});

test.each([
  [
    "Observaciones",
    "listObservationsPage",
    "createObservation",
    "Nueva observación",
    "Descripción",
    "Registrar observación",
    { description: "Demo" },
  ],
  [
    "Contactos",
    "listEmergencyContactsPage",
    "createEmergencyContact",
    "Nuevo contacto",
    "Nombre",
    "Registrar contacto",
    { name: "Demo", phone_number: "5550000", relationship_label: "Familiar" },
  ],
])(
  "consulta y crea %s sin ventanas apiladas",
  async (tab, listMethod, createMethod, title, field, submit, payload) => {
    const user = userEvent.setup();
    renderRecord();
    await screen.findByRole("tab", { name: tab });
    await openTab(user, tab);
    await waitFor(() => expect(students[listMethod]).toHaveBeenCalled());
    await user.click(screen.getByRole("button", { name: title }));
    await user.type(
      screen.getByLabelText(new RegExp(field)),
      payload.name ?? payload.description
    );
    if (tab === "Contactos") {
      await user.type(screen.getByLabelText(/Teléfono/), payload.phone_number);
      await user.type(
        screen.getByLabelText(/Relación/),
        payload.relationship_label
      );
    }
    await user.click(screen.getByRole("button", { name: submit }));
    await waitFor(() =>
      expect(students[createMethod]).toHaveBeenCalledWith("student-1", payload)
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  }
);

test("un rechazo sensible ofrece reintento y permite seguir consultando datos básicos", async () => {
  students.listHealthNotesPage.mockRejectedValueOnce(
    new Error("Sin permiso sensible")
  );
  students.listHealthNotesPage.mockResolvedValue(paged([note]));
  const user = userEvent.setup();
  renderRecord("/app/alumnos/student-1?tab=health");
  await screen.findByText("Sin permiso sensible");
  expect(screen.queryByText("Sin notas de salud")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Reintentar" }));
  await screen.findByText(note.content);
  await openTab(user, "Datos");
  expect(screen.getByText(RECORD.person.address)).toBeInTheDocument();
});

test("edita todos los campos disponibles en línea sin incluir CUI ni nacimiento", async () => {
  const updated = {
    ...RECORD,
    person: {
      ...RECORD.person,
      ...editedInstitutionalPerson,
      last_name: "Nuevo",
    },
  };
  students.getRecord.mockResolvedValue({
    ...RECORD,
    actions: { deactivate: true },
  });
  students.update.mockResolvedValue(updated);
  const user = userEvent.setup();
  renderRecord();
  await screen.findByText(RECORD.person.address);
  await user.click(screen.getByRole("button", { name: "Editar" }));
  expect(screen.queryByLabelText(/^CUI/)).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/^Estado/)).not.toBeInTheDocument();
  await editInstitutionalPerson(user);
  await user.clear(screen.getByLabelText(/^Apellidos/));
  await user.type(screen.getByLabelText(/^Apellidos/), "Nuevo");
  await user.click(screen.getByRole("button", { name: "Guardar cambios" }));
  await waitFor(() =>
    expect(students.update).toHaveBeenCalledWith(
      1,
      expect.objectContaining({
        person: expect.objectContaining(editedInstitutionalPerson),
      })
    )
  );
  expect(
    await screen.findByRole("heading", { name: "Alumno Nuevo" })
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Desactivar estudiante" })
  ).toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("consulta encargados y vincula usando catálogo paginado", async () => {
  guardians.listPage.mockResolvedValue(
    paged([{ id: 7, person: { first_name: "Encargado", last_name: "Demo" } }])
  );
  const user = userEvent.setup();
  renderRecord("/app/alumnos/student-1?tab=guardians");
  await screen.findByText("Sin encargados vinculados");
  await user.click(screen.getByRole("button", { name: "Vincular encargado" }));
  await user.click(
    await screen.findByRole("button", { name: "Elegir Encargado Demo" })
  );
  await user.type(
    screen.getByLabelText(/Parentesco o responsabilidad/),
    "Familiar"
  );
  await user.click(screen.getByRole("button", { name: "Vincular encargado" }));
  await waitFor(() =>
    expect(students.linkRecordGuardian).toHaveBeenCalledWith("student-1", {
      guardian_id: 7,
      relationship_label: "Familiar",
    })
  );
  expect(guardians.listPage).toHaveBeenCalledWith({ page: 1, search: "" });
});

test("muestra matrícula vigente e historial con nombres del servidor", async () => {
  enrolments.listStudentRecord.mockResolvedValue(
    paged([
      {
        public_id: "e1",
        cycle_name: "Ciclo Demo",
        grade_name: "Primero",
        section_name: "A",
        shift_name: "Matutina",
        status: "active",
        is_current: true,
        effective_on: "2026-02-01",
      },
    ])
  );
  renderRecord("/app/alumnos/student-1?tab=enrolments");
  expect(
    await screen.findByText(/Ciclo Demo · Primero · Sección A · Matutina/)
  ).toBeInTheDocument();
  expect(screen.getByText(/Matrícula vigente/)).toBeInTheDocument();
  expect(enrolments.listStudentRecord).toHaveBeenCalledWith(
    "student-1",
    expect.objectContaining({ page: 1 })
  );
});

test("documentos del alumno y descarga autorizada no se guardan en almacenamiento local", async () => {
  const store = vi.spyOn(Storage.prototype, "setItem");
  documents.listStudentRecords.mockResolvedValue(
    paged([
      {
        public_id: "d1",
        filename: "demo.pdf",
        version_number: 2,
        is_active: true,
      },
    ])
  );
  documents.issueDownloadToken.mockResolvedValue({
    download_url: "/api/v1/documents/records/d1/download/?token=demo",
  });
  const user = userEvent.setup();
  renderRecord("/app/alumnos/student-1?tab=documents");
  await screen.findByText(/demo.pdf · Versión 2/);
  await user.click(screen.getByRole("button", { name: "Preparar descarga" }));
  const link = await screen.findByRole("link", { name: "Descargar demo.pdf" });
  expect(link).toHaveAttribute(
    "href",
    "/api/v1/documents/records/d1/download/?token=demo"
  );
  expect(documents.issueDownloadToken).toHaveBeenCalledWith("d1");
  expect(store).not.toHaveBeenCalled();
});

test("asistencia solicita únicamente el UUID del expediente visible", async () => {
  attendance.listEvents.mockResolvedValue(
    paged([
      {
        public_id: "a1",
        event_date: "2026-02-01",
        movement_type: "entry",
        origin: "manual",
        captured_at: "2026-02-01T12:00:00Z",
      },
    ])
  );
  renderRecord("/app/alumnos/student-1?tab=attendance");
  await screen.findByText(/Entrada/);
  expect(attendance.listEvents).toHaveBeenCalledWith({
    page: 1,
    student_id: "student-1",
  });
});

test("descarta una respuesta tardía al navegar a otro alumno", async () => {
  let finish;
  students.getRecord.mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      })
  );
  students.getRecord.mockResolvedValue({
    ...RECORD,
    public_id: "student-2",
    person: { ...RECORD.person, first_name: "Otro" },
  });
  const user = userEvent.setup();
  renderRecord();
  await user.click(screen.getByRole("link", { name: "Otro estudiante" }));
  await screen.findByRole("heading", { name: "Otro Demo" });
  await act(async () => finish(RECORD));
  expect(
    screen.queryByRole("heading", { name: "Alumno Demo" })
  ).not.toBeInTheDocument();
});

test("la denegación del expediente no monta pestañas ni consulta datos relacionados", async () => {
  students.getRecord.mockRejectedValue(new Error("Acceso denegado"));
  renderRecord("/app/alumnos/student-1?tab=health");
  await screen.findByText("Acceso denegado");
  expect(screen.queryByRole("tab")).not.toBeInTheDocument();
  expect(students.listHealthNotesPage).not.toHaveBeenCalled();
});

const DEACTIVATABLE = {
  ...RECORD,
  is_active: true,
  actions: { deactivate: true },
};
const DEACTIVATED = {
  ...RECORD,
  status: "inactive",
  is_active: false,
  actions: { deactivate: false },
};

test("E7 requiere confirmacion y cancelar conserva al estudiante", async () => {
  students.getRecord.mockResolvedValue(DEACTIVATABLE);
  const user = userEvent.setup();
  renderRecord();
  await user.click(
    await screen.findByRole("button", { name: "Desactivar estudiante" })
  );
  expect(
    screen.getByRole("heading", { name: "Desactivar estudiante: Alumno Demo" })
  ).toHaveFocus();
  expect(students.deactivate).not.toHaveBeenCalled();
  await user.click(screen.getByRole("button", { name: "Cancelar" }));
  expect(students.deactivate).not.toHaveBeenCalled();
  expect(
    screen.getByRole("button", { name: "Desactivar estudiante" })
  ).toBeInTheDocument();
});

test("E7 confirma desactivacion y recarga el estado del servidor", async () => {
  students.getRecord
    .mockResolvedValueOnce(DEACTIVATABLE)
    .mockResolvedValue(DEACTIVATED);
  const user = userEvent.setup();
  renderRecord();
  await user.click(
    await screen.findByRole("button", { name: "Desactivar estudiante" })
  );
  await user.click(
    screen.getByRole("button", { name: "Confirmar desactivación" })
  );
  await screen.findByText("Estudiante desactivado. El historial se conserva.");
  await screen.findByText("Inactivo");
  expect(students.deactivate).toHaveBeenCalledExactlyOnceWith(1);
  expect(students.getRecord).toHaveBeenCalledTimes(2);
  expect(
    screen.queryByRole("button", { name: "Desactivar estudiante" })
  ).not.toBeInTheDocument();
});

test("E7 respeta capacidad de solo lectura aunque el perfil este activo", async () => {
  students.getRecord.mockResolvedValue({
    ...DEACTIVATABLE,
    actions: { deactivate: false },
  });
  renderRecord();
  await screen.findByRole("heading", { name: "Alumno Demo" });
  expect(
    screen.queryByRole("button", { name: "Desactivar estudiante" })
  ).not.toBeInTheDocument();
});

test("E7 conserva confirmacion ante rechazo sin mostrar exito", async () => {
  students.getRecord.mockResolvedValue(DEACTIVATABLE);
  students.deactivate.mockRejectedValue(
    new Error("Sin permiso para desactivar")
  );
  const user = userEvent.setup();
  renderRecord();
  await user.click(
    await screen.findByRole("button", { name: "Desactivar estudiante" })
  );
  await user.click(
    screen.getByRole("button", { name: "Confirmar desactivación" })
  );
  await screen.findByText("Sin permiso para desactivar");
  expect(
    screen.getByRole("button", { name: "Confirmar desactivación" })
  ).toBeEnabled();
  expect(
    screen.queryByText("Estudiante desactivado. El historial se conserva.")
  ).not.toBeInTheDocument();
  expect(students.getRecord).toHaveBeenCalledTimes(1);
});

test("E7 distingue escritura confirmada de error al recargar y no repite DELETE", async () => {
  students.getRecord
    .mockResolvedValueOnce(DEACTIVATABLE)
    .mockRejectedValueOnce(new Error("Lectura temporalmente no disponible"))
    .mockResolvedValue(DEACTIVATED);
  const user = userEvent.setup();
  renderRecord();
  await user.click(
    await screen.findByRole("button", { name: "Desactivar estudiante" })
  );
  await user.click(
    screen.getByRole("button", { name: "Confirmar desactivación" })
  );
  await screen.findByText("Lectura temporalmente no disponible");
  expect(
    screen.getByText("Estudiante desactivado. El historial se conserva.")
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Confirmar desactivación" })
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Reintentar" }));
  await screen.findByText("Inactivo");
  expect(students.deactivate).toHaveBeenCalledTimes(1);
});

test("E7 bloquea doble envio y navegacion durante DELETE", async () => {
  students.getRecord
    .mockResolvedValueOnce(DEACTIVATABLE)
    .mockResolvedValue(DEACTIVATED);
  let resolve;
  students.deactivate.mockReturnValue(
    new Promise((done) => {
      resolve = done;
    })
  );
  const user = userEvent.setup();
  renderRecord();
  await user.click(
    await screen.findByRole("button", { name: "Desactivar estudiante" })
  );
  await user.click(
    screen.getByRole("button", { name: "Confirmar desactivación" })
  );
  expect(screen.getByRole("button", { name: "Guardando…" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Cancelar" })).toBeDisabled();
  expect(screen.getByRole("tab", { name: "Salud" })).toBeDisabled();
  expect(students.deactivate).toHaveBeenCalledTimes(1);
  await act(async () => resolve(null));
  await screen.findByText("Inactivo");
});
