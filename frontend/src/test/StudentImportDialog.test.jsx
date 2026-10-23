import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

const studentsServiceMock = vi.hoisted(() => ({
  previewImport: vi.fn(),
  confirmImport: vi.fn(),
}));

vi.mock("@students/studentsService.js", () => ({
  studentsService: studentsServiceMock,
}));

import { StudentImportDialog } from "@students/StudentImportDialog.jsx";

import { renderWithRouter } from "./helpers/renderWithRouter.jsx";

const ROW = {
  line: 2,
  data: {
    nombres: "Ana",
    apellidos: "Perez",
    cui: "1234567890101",
    fecha_nacimiento: "2012-03-04",
    sexo: "F",
    correo: "",
    telefono: "",
    codigo_estudiante: "",
  },
  status: "ready",
  errors: [],
};
const READY = {
  file_sha256: "abc123",
  summary: { total: 1, ready: 1, errors: 0 },
  rows: [ROW],
};
const WITH_ERRORS = {
  file_sha256: "abc123",
  summary: { total: 2, ready: 1, errors: 1 },
  rows: [
    ROW,
    {
      ...ROW,
      line: 3,
      data: { ...ROW.data, nombres: "Beto" },
      status: "error",
      errors: ["El CUI se repite en la línea 2."],
    },
  ],
};

function httpError(status, payload, message = "Solicitud no completada.") {
  const error = new Error(message);
  error.status = status;
  error.payload = payload;
  return error;
}

async function uploadAndValidate(user) {
  const file = new File(["nombres,apellidos\nAna,Perez\n"], "alumnos.csv", {
    type: "text/csv",
  });
  await user.upload(screen.getByLabelText("Archivo CSV"), file);
  await user.click(screen.getByRole("button", { name: "Validar archivo" }));
  return file;
}

beforeEach(() => {
  Object.values(studentsServiceMock).forEach((mock) => mock.mockReset());
});

describe("StudentImportDialog", () => {
  test("Confirmar inserción queda deshabilitado mientras haya errores", async () => {
    studentsServiceMock.previewImport.mockResolvedValue(WITH_ERRORS);
    const user = userEvent.setup();
    renderWithRouter(
      <StudentImportDialog
        onClose={vi.fn()}
        onDownloadTemplate={vi.fn()}
        open
      />
    );

    expect(
      screen.getByRole("button", { name: "Validar archivo" })
    ).toBeDisabled();
    const file = await uploadAndValidate(user);

    expect(studentsServiceMock.previewImport).toHaveBeenCalledWith(file);
    expect(
      await screen.findByText("El CUI se repite en la línea 2.")
    ).toBeInTheDocument();
    expect(screen.getByText("Con errores")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Confirmar inserción" })
    ).toBeDisabled();
  });

  test("confirma sin errores y muestra cuántos se crearon", async () => {
    studentsServiceMock.previewImport.mockResolvedValue(READY);
    studentsServiceMock.confirmImport.mockResolvedValue({
      created: 1,
      students: [
        { public_id: "s-1", student_code: "EST-1", full_name: "Ana Perez" },
      ],
    });
    const user = userEvent.setup();
    renderWithRouter(
      <StudentImportDialog
        onClose={vi.fn()}
        onDownloadTemplate={vi.fn()}
        open
      />
    );

    const file = await uploadAndValidate(user);
    await user.click(
      await screen.findByRole("button", { name: "Confirmar inserción" })
    );

    await waitFor(() =>
      expect(studentsServiceMock.confirmImport).toHaveBeenCalledWith(
        file,
        "abc123"
      )
    );
    expect(
      await screen.findByText("Se crearon 1 estudiantes.")
    ).toBeInTheDocument();
  });

  test("un 422 muestra las filas rechazadas y no cierra el diálogo", async () => {
    studentsServiceMock.previewImport.mockResolvedValue(READY);
    studentsServiceMock.confirmImport.mockRejectedValue(
      httpError(422, WITH_ERRORS)
    );
    const onClose = vi.fn();
    const user = userEvent.setup();
    renderWithRouter(
      <StudentImportDialog
        onClose={onClose}
        onDownloadTemplate={vi.fn()}
        open
      />
    );

    await uploadAndValidate(user);
    await user.click(
      await screen.findByRole("button", { name: "Confirmar inserción" })
    );

    expect(
      await screen.findByText(/No se insertó ningún estudiante/)
    ).toBeInTheDocument();
    expect(
      screen.getByText("El CUI se repite en la línea 2.")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Confirmar inserción" })
    ).toBeDisabled();
    expect(onClose).not.toHaveBeenCalled();
  });

  test("un 409 pide volver a validar el archivo", async () => {
    studentsServiceMock.previewImport.mockResolvedValue(READY);
    studentsServiceMock.confirmImport.mockRejectedValue(
      httpError(409, { detail: "El archivo cambió." })
    );
    const user = userEvent.setup();
    renderWithRouter(
      <StudentImportDialog
        onClose={vi.fn()}
        onDownloadTemplate={vi.fn()}
        open
      />
    );

    await uploadAndValidate(user);
    await user.click(
      await screen.findByRole("button", { name: "Confirmar inserción" })
    );

    expect(
      await screen.findByText(/El archivo cambió desde la vista previa/)
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Volver a validar" })
    ).toBeInTheDocument();
  });

  test("un error estructural del archivo se muestra en el primer paso", async () => {
    studentsServiceMock.previewImport.mockRejectedValue(
      httpError(400, null, "Faltan columnas obligatorias: nombres.")
    );
    const user = userEvent.setup();
    renderWithRouter(
      <StudentImportDialog
        onClose={vi.fn()}
        onDownloadTemplate={vi.fn()}
        open
      />
    );

    await uploadAndValidate(user);
    expect(
      await screen.findByText("Faltan columnas obligatorias: nombres.")
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Validar archivo" })
    ).toBeInTheDocument();
  });
});
