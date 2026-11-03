import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useLocation } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

const evaluationServiceMock = vi.hoisted(() => ({
  getGlobalConfig: vi.fn(),
  getCycleConfig: vi.fn(),
  updateGlobalConfig: vi.fn(),
  updateCycleConfig: vi.fn(),
  cloneConfig: vi.fn(),
  listUnits: vi.fn(),
  createUnit: vi.fn(),
  closeUnit: vi.fn(),
  updateRecoveryWindow: vi.fn(),
  listCaptureExceptions: vi.fn(),
  createCaptureException: vi.fn(),
}));
const cyclesServiceMock = vi.hoisted(() => ({ list: vi.fn() }));
const teachersServiceMock = vi.hoisted(() => ({ listPage: vi.fn() }));

vi.mock("@evaluation/evaluationService.js", async (importOriginal) => {
  const original = await importOriginal();
  return { ...original, evaluationService: evaluationServiceMock };
});
vi.mock("@cycles/cyclesService.js", async (importOriginal) => {
  const original = await importOriginal();
  return { ...original, cyclesService: cyclesServiceMock };
});
vi.mock("@academics/academicsService.js", async () => {
  const { academicsServiceMock } = await import("./mocks/academicsService.js");
  return { academicsService: academicsServiceMock, PAGE_SIZE: 25 };
});
vi.mock("@teachers/teachersService.js", () => ({
  teachersService: teachersServiceMock,
}));

import { EvaluationPage } from "@evaluation/EvaluationPage.jsx";
import { paginated } from "./fixtures/academics.js";
import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";
import { selectOption } from "./helpers/selectOption.jsx";
import {
  academicsServiceMock,
  resetAcademicsServiceMock,
} from "./mocks/academicsService.js";

const CONFIGURE = "evaluation.configure_units";
const ADMIN = sessionUser([CONFIGURE, "grade.write", "student.view_basic"]);

const ACTIVE = {
  public_id: "c-2026",
  year: 2026,
  name: "Ciclo 2026",
  status: "active",
  starts_on: "2026-01-15",
  ends_on: "2026-10-30",
};
const DRAFT = {
  ...ACTIVE,
  public_id: "c-2027",
  year: 2027,
  name: "Ciclo 2027",
  status: "draft",
};
const UNIT = {
  public_id: "u-4",
  number: 4,
  name: "Cuarta unidad",
  status: "open",
  starts_on: "2026-08-01",
  ends_on: "2026-10-30",
  capture_starts_on: "2026-09-01",
  capture_ends_on: "2026-10-30",
  recovery_starts_on: null,
  recovery_ends_on: null,
};
const CLOSED_UNIT = {
  ...UNIT,
  public_id: "u-1",
  number: 1,
  name: "Primera unidad",
  status: "closed",
};

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.search}</output>;
}

function renderPage(route = "/app/evaluacion", user = ADMIN) {
  return renderWithSession(
    <>
      <EvaluationPage />
      <LocationProbe />
    </>,
    { user, route }
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  resetAcademicsServiceMock();
  cyclesServiceMock.list.mockResolvedValue(paginated([DRAFT, ACTIVE]));
  evaluationServiceMock.getGlobalConfig.mockResolvedValue({
    default_unit_count: 4,
  });
  evaluationServiceMock.getCycleConfig.mockRejectedValue(new Error("404"));
  evaluationServiceMock.listUnits.mockResolvedValue(
    paginated([CLOSED_UNIT, UNIT])
  );
  evaluationServiceMock.listCaptureExceptions.mockResolvedValue(paginated([]));
  teachersServiceMock.listPage.mockResolvedValue(paginated([]));
});

describe("Evaluación: página con pestañas (1.5)", () => {
  test("abre el ciclo activo en Unidades y lista sus unidades con tildes", async () => {
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Evaluación" })
    ).toBeInTheDocument();
    expect(await screen.findByText("Cuarta unidad")).toBeInTheDocument();
    expect(evaluationServiceMock.listUnits).toHaveBeenCalledWith(
      "c-2026",
      expect.objectContaining({ page: 1 })
    );
    for (const label of ["Período", "Recuperación", "N.º"]) {
      expect(
        screen.getByRole("columnheader", { name: label })
      ).toBeInTheDocument();
    }
    expect(screen.getAllByText("Sin ventana").length).toBeGreaterThan(0);
    expect(screen.getByRole("tab", { name: "Unidades" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
  });

  test("el ciclo elegido y la pestaña viven en la URL", async () => {
    const user = userEvent.setup();
    renderPage("/app/evaluacion?ciclo=c-2027&tab=unidades");

    await waitFor(() =>
      expect(evaluationServiceMock.listUnits).toHaveBeenCalledWith(
        "c-2027",
        expect.anything()
      )
    );
    await selectOption(user, "Ciclo escolar", /Ciclo 2026/);
    await waitFor(() =>
      expect(screen.getByTestId("location")).toHaveTextContent("ciclo=c-2026")
    );
  });

  test("sin permisos de captura no muestra Planilla ni Avance", async () => {
    renderPage("/app/evaluacion", sessionUser(["student.view_basic"]));

    expect(
      await screen.findByRole("tab", { name: "Recuperación" })
    ).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Planilla" })).toBeNull();
    expect(screen.queryByRole("tab", { name: "Avance" })).toBeNull();
    // Sin configurar tampoco hay acciones de configuración.
    expect(await screen.findByText("Cuarta unidad")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Nueva unidad" })).toBeNull();
  });
});

describe("Unidades: cierre, alta y clonado (V1, V6)", () => {
  test("Cerrar unidad confirma y llama al cierre", async () => {
    const user = userEvent.setup();
    evaluationServiceMock.closeUnit.mockResolvedValue({
      ...UNIT,
      status: "closed",
    });
    renderPage();

    await user.click(
      await screen.findByRole("button", { name: "Acciones de Cuarta unidad" })
    );
    await user.click(screen.getByRole("menuitem", { name: "Cerrar unidad" }));
    const dialog = await screen.findByRole("dialog", {
      name: "Cerrar unidad de evaluación",
    });
    expect(dialog).toHaveTextContent("requisito para cerrar el ciclo escolar");
    await user.click(
      within(dialog).getByRole("button", { name: "Cerrar unidad" })
    );

    await waitFor(() =>
      expect(evaluationServiceMock.closeUnit).toHaveBeenCalledWith(
        "c-2026",
        "u-4"
      )
    );
  });

  test("una unidad cerrada no ofrece cerrarse otra vez", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(
      await screen.findByRole("button", {
        name: "Acciones de Primera unidad",
      })
    );
    expect(
      screen.getByRole("menuitem", { name: "Abrir planilla" })
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("menuitem", { name: "Cerrar unidad" })
    ).toBeNull();
  });

  test("sin evaluation.configure_units no hay Cerrar unidad", async () => {
    const user = userEvent.setup();
    renderPage("/app/evaluacion", sessionUser(["grade.write"]));

    await user.click(
      await screen.findByRole("button", { name: "Acciones de Cuarta unidad" })
    );
    expect(
      screen.queryByRole("menuitem", { name: "Cerrar unidad" })
    ).toBeNull();
    expect(
      screen.queryByRole("menuitem", {
        name: "Ajustar ventana de recuperación",
      })
    ).toBeNull();
  });

  test("Nueva unidad exige las dos fechas de recuperación o ninguna", async () => {
    const user = userEvent.setup();
    evaluationServiceMock.createUnit.mockResolvedValue(UNIT);
    renderPage();

    await user.click(
      await screen.findByRole("button", { name: "Nueva unidad" })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Nueva unidad de evaluación",
    });
    const fill = (label, value) =>
      fireEvent.change(within(dialog).getByLabelText(label), {
        target: { value },
      });
    await user.type(within(dialog).getByLabelText(/^Nombre/), "Quinta unidad");
    fill(/Inicio del período/, "2026-08-01");
    fill(/Fin del período/, "2026-10-30");
    fill(/Captura desde/, "2026-09-01");
    fill(/Captura hasta/, "2026-10-30");
    fill(/Recuperación desde/, "2026-11-01");
    await user.click(
      within(dialog).getByRole("button", { name: "Crear unidad" })
    );

    expect(
      await within(dialog).findByText(/Escriba las dos fechas/)
    ).toBeInTheDocument();
    expect(evaluationServiceMock.createUnit).not.toHaveBeenCalled();

    fill(/Recuperación desde/, "");
    await user.click(
      within(dialog).getByRole("button", { name: "Crear unidad" })
    );

    await waitFor(() =>
      expect(evaluationServiceMock.createUnit).toHaveBeenCalledWith("c-2026", {
        number: 3,
        name: "Quinta unidad",
        starts_on: "2026-08-01",
        ends_on: "2026-10-30",
        capture_starts_on: "2026-09-01",
        capture_ends_on: "2026-10-30",
      })
    );
  });

  test("clona la configuración a un ciclo en borrador", async () => {
    const user = userEvent.setup();
    evaluationServiceMock.cloneConfig.mockResolvedValue([]);
    renderPage();

    await user.click(
      await screen.findByRole("button", {
        name: "Clonar configuración a otro ciclo",
      })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Clonar configuración a otro ciclo",
    });
    await selectOption(user, /Ciclo destino/, "Ciclo 2027", dialog);
    await user.click(
      within(dialog).getByRole("button", { name: "Clonar configuración" })
    );

    await waitFor(() =>
      expect(evaluationServiceMock.cloneConfig).toHaveBeenCalledWith(
        "c-2026",
        "c-2027"
      )
    );
    expect(
      await within(dialog).findByText(/se copió a «Ciclo 2027»/)
    ).toBeInTheDocument();
  });

  test("el rechazo del clonado se muestra sin cerrar la ventana", async () => {
    const user = userEvent.setup();
    evaluationServiceMock.cloneConfig.mockRejectedValue(
      new Error("El ciclo destino ya tiene unidades de evaluación.")
    );
    renderPage();

    await user.click(
      await screen.findByRole("button", {
        name: "Clonar configuración a otro ciclo",
      })
    );
    const dialog = await screen.findByRole("dialog", {
      name: "Clonar configuración a otro ciclo",
    });
    await selectOption(user, /Ciclo destino/, "Ciclo 2027", dialog);
    await user.click(
      within(dialog).getByRole("button", { name: "Clonar configuración" })
    );
    expect(
      await within(dialog).findByText(
        "El ciclo destino ya tiene unidades de evaluación."
      )
    ).toBeInTheDocument();
  });
});

describe("Permisos excepcionales de captura", () => {
  test("lista en el servidor y otorga con selectores de búsqueda", async () => {
    const user = userEvent.setup();
    academicsServiceMock.listSubjects.mockResolvedValue(
      paginated([{ public_id: "sub-mat", name: "Matemática", code: "MAT" }])
    );
    teachersServiceMock.listPage.mockResolvedValue(
      paginated([
        {
          public_id: "t-1",
          employee_code: "DOC-1",
          person: { public_id: "p-9", first_name: "Rosa", last_name: "Pérez" },
        },
      ])
    );
    evaluationServiceMock.createCaptureException.mockResolvedValue({});
    renderPage();

    await user.click(
      await screen.findByRole("button", { name: "Acciones de Cuarta unidad" })
    );
    await user.click(
      screen.getByRole("menuitem", {
        name: "Permisos excepcionales de captura",
      })
    );
    await screen.findByRole("dialog", {
      name: "Permisos excepcionales de captura",
    });
    await waitFor(() =>
      expect(evaluationServiceMock.listCaptureExceptions).toHaveBeenCalledWith(
        "c-2026",
        "u-4",
        expect.objectContaining({ page: 1 })
      )
    );

    await user.click(screen.getByRole("button", { name: "Otorgar excepción" }));
    const form = await screen.findByRole("dialog", {
      name: "Nueva excepción de captura",
    });
    await user.type(
      await within(form).findByRole("combobox", { name: /Subárea/ }),
      "Mat"
    );
    await user.click(await screen.findByRole("option", { name: /Matemática/ }));
    await user.type(
      within(form).getByRole("combobox", { name: /Docente/ }),
      "Rosa"
    );
    await user.click(
      await screen.findByRole("option", { name: "Rosa Pérez · DOC-1" })
    );
    await user.type(
      within(form).getByLabelText(/Motivo de la excepción/),
      "Licencia médica"
    );
    fireEvent.change(within(form).getByLabelText(/Vence el/), {
      target: { value: "2026-11-15" },
    });
    await user.click(
      within(form).getByRole("button", { name: "Otorgar excepción" })
    );

    await waitFor(() =>
      expect(evaluationServiceMock.createCaptureException).toHaveBeenCalledWith(
        "c-2026",
        "u-4",
        {
          subject: "sub-mat",
          teacher: "p-9",
          reason: "Licencia médica",
          expires_at: "2026-11-15",
        }
      )
    );
  });
});
