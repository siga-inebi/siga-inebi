import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

const studentsServiceMock = vi.hoisted(() => ({
  listPage: vi.fn(),
  list: vi.fn(),
}));
const teachersServiceMock = vi.hoisted(() => ({
  listPage: vi.fn(),
  list: vi.fn(),
}));
const guardiansServiceMock = vi.hoisted(() => ({
  listPage: vi.fn(),
  list: vi.fn(),
}));
const cyclesServiceMock = vi.hoisted(() => ({ list: vi.fn() }));
const enrolmentsServiceMock = vi.hoisted(() => ({ listActive: vi.fn() }));
const reportingServiceMock = vi.hoisted(() => ({ listAlerts: vi.fn() }));
vi.mock("@students/studentsService.js", () => ({
  studentsService: studentsServiceMock,
}));
vi.mock("@teachers/teachersService.js", () => ({
  teachersService: teachersServiceMock,
}));
vi.mock("@guardians/guardiansService.js", () => ({
  guardiansService: guardiansServiceMock,
}));
vi.mock("@cycles/cyclesService.js", () => ({
  cyclesService: cyclesServiceMock,
}));
vi.mock("@enrolments/enrolmentsService.js", () => ({
  enrolmentsService: enrolmentsServiceMock,
}));
vi.mock("@reporting/reportingService.js", () => ({
  reportingService: reportingServiceMock,
}));
const authServiceMock = vi.hoisted(() => ({
  myAccount: vi.fn(),
  mySchedule: vi.fn(),
  passwordPolicy: vi.fn(),
}));
vi.mock("@auth/authService.js", () => ({ authService: authServiceMock }));

import { MyAccountPage } from "@auth/MyAccountPage.jsx";
import { DashboardPage } from "@dashboard/DashboardPage.jsx";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import { existingPersonField } from "@people/existingPersonSearch.js";
import {
  defineCatalog,
  useCatalogOptions,
} from "@shared/catalogs/useCatalogOptions.js";

import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";

beforeEach(() => {
  studentsServiceMock.listPage.mockReset().mockResolvedValue({ count: 1250 });
  teachersServiceMock.listPage.mockReset().mockResolvedValue({ count: 40 });
  guardiansServiceMock.listPage.mockReset().mockResolvedValue({ count: 900 });
  cyclesServiceMock.list.mockReset().mockResolvedValue({
    count: 2,
    results: [
      {
        public_id: "cycle-active",
        name: "Ciclo 2026",
        year: 2026,
        status: "active",
        starts_on: "2026-01-15",
        ends_on: "2026-10-31",
      },
      {
        public_id: "cycle-draft",
        name: "Ciclo 2027",
        year: 2027,
        status: "draft",
        starts_on: "2027-01-15",
        ends_on: "2027-10-31",
      },
    ],
  });
  enrolmentsServiceMock.listActive
    .mockReset()
    .mockResolvedValue({ count: 1180 });
  reportingServiceMock.listAlerts
    .mockReset()
    .mockResolvedValue({ count: 0, results: [] });
  studentsServiceMock.list.mockReset();
});

describe("Panel principal (1.7, MC3)", () => {
  test("resume la operacion sin descargar padrones y enlaza el ciclo activo", async () => {
    renderWithSession(<DashboardPage />, {
      user: sessionUser(["student.view_basic"]),
      route: "/app",
    });

    expect(await screen.findByText("1250")).toBeInTheDocument();
    expect(screen.getByText("40")).toBeInTheDocument();
    expect(studentsServiceMock.listPage).toHaveBeenCalledWith({ page_size: 1 });
    expect(studentsServiceMock.list).not.toHaveBeenCalled();
    expect(await screen.findByText("1180")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Ciclo 2026" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Abrir ciclo activo/i })
    ).toHaveAttribute("href", "/app/ciclos/cycle-active");
    expect(screen.queryByText(/Estado del servicio/i)).not.toBeInTheDocument();
  });

  test("prioriza alertas activas para una cuenta autorizada", async () => {
    reportingServiceMock.listAlerts.mockResolvedValue({
      count: 2,
      results: [
        {
          public_id: "alert-1",
          alert_type: "inconsistencia",
          event_date: "2026-10-18",
        },
      ],
    });
    renderWithSession(<DashboardPage />, {
      user: sessionUser(["student.view_basic", "reporting.alert.view"]),
      route: "/app",
    });

    expect(await screen.findByText("2 alertas")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Atender alertas/i })
    ).toHaveAttribute("href", "/app/alertas");
    expect(screen.getByText("Inconsistencia")).toBeInTheDocument();
  });
});

describe("Mi cuenta (MC1)", () => {
  test("muestra datos, roles con alcance y sesiones", async () => {
    authServiceMock.myAccount.mockResolvedValue({
      account: {
        public_id: "a",
        username: "ana.lopez",
        email: "ana@example.test",
        status: "active",
        status_display: "Activa",
      },
      person: {
        first_name: "Ana",
        last_name: "López",
        email: "ana@example.test",
        phone_number: "5555-0000",
      },
      roles: [
        {
          public_id: "as-1",
          role_name: "Docente",
          ends_at: null,
          status: "active",
          status_display: "Vigente",
          scopes: [
            {
              public_id: "sg",
              dimensions: [
                { dimension: "section", label: "Primero Básico A" },
                { dimension: "subject", label: "Matemática" },
              ],
            },
          ],
        },
      ],
      sessions: [
        {
          last_activity_at: "2026-10-17T15:00:00Z",
          expires_at: "2026-10-17T16:00:00Z",
          is_current: true,
        },
      ],
      session_idle_timeout_minutes: 60,
      permissions: ["grade.write"],
    });
    authServiceMock.mySchedule.mockResolvedValue({ count: 0, results: [] });
    renderWithSession(<MyAccountPage />, {
      user: sessionUser(),
      route: "/app/mi-cuenta",
    });

    expect(
      await screen.findByText("Primero Básico A · Matemática")
    ).toBeInTheDocument();
    expect(screen.getByText("Esta sesión")).toBeInTheDocument();
    expect(
      screen.getByText(/60 minutos \(el mayor de sus roles\)/)
    ).toBeInTheDocument();
  });
});

describe("Mi horario como reja semanal (S4)", () => {
  test("pinta cada clase en su día y bloque", async () => {
    authServiceMock.myAccount.mockResolvedValue({
      account: {
        public_id: "a",
        username: "ana.lopez",
        status: "active",
        status_display: "Activa",
      },
      person: { first_name: "Ana", last_name: "López" },
      roles: [],
      sessions: [],
      session_idle_timeout_minutes: 30,
      permissions: [],
    });
    const block = {
      public_id: "b-1",
      number: 1,
      name: "Bloque 1",
      starts_on: "07:30:00",
      ends_on: "08:15:00",
    };
    authServiceMock.mySchedule.mockResolvedValue({
      count: 1,
      results: [
        {
          public_id: "cs-1",
          day_of_week: 3,
          day_of_week_display: "Miércoles",
          schedule_block: block,
          subject: { public_id: "m", name: "Matemática" },
          section: { public_id: "s", name: "A", grade: { name: "Primero" } },
        },
      ],
    });
    renderWithSession(<MyAccountPage />, {
      user: sessionUser(),
      route: "/app/mi-cuenta",
    });

    const grid = await screen.findByRole("table", {
      name: "Mi horario semanal",
    });
    const headers = within(grid).getAllByRole("columnheader");
    expect(headers.map((header) => header.textContent)).toEqual([
      "Bloque",
      "Lunes",
      "Martes",
      "Miércoles",
      "Jueves",
      "Viernes",
    ]);
    const row = within(grid).getByRole("row", {
      name: /Bloque 1 · 07:30–08:15/,
    });
    const cells = within(row).getAllByRole("cell");
    expect(cells[2]).toHaveTextContent("Matemática");
    expect(cells[2]).toHaveTextContent("Primero A");
    expect(cells[0]).toBeEmptyDOMElement();
  });
});

describe("Selector con busqueda remota en EntityFormWindow (1.3)", () => {
  test("busca en el servidor mientras se escribe y envia el valor elegido", async () => {
    const user = userEvent.setup();
    const fetchPage = vi.fn(async ({ search }) => ({
      results: [{ public_id: "t-1", name: `Docente ${search}` }],
    }));
    const onSubmit = vi.fn();
    renderWithSession(
      <EntityFormWindow
        fields={[
          {
            name: "teacher_id",
            label: "Docente",
            type: "search-select",
            required: true,
            search: {
              name: "teachers-test",
              fetchPage,
              mapResult: (row) => ({ value: row.public_id, label: row.name }),
            },
          },
        ]}
        initialValues={{ teacher_id: "" }}
        onCancel={vi.fn()}
        onSubmit={onSubmit}
        open
        title="Nueva asignación"
      />,
      { user: sessionUser() }
    );

    await user.type(await screen.findByLabelText(/Docente/), "Mar");
    await user.click(await screen.findByText("Docente Mar"));
    await user.click(screen.getByRole("button", { name: "Guardar" }));

    expect(fetchPage).toHaveBeenCalledWith({ search: "Mar" });
    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({ teacher_id: "t-1" })
    );
  });

  test("elegir una persona registrada precarga sus datos salvo CUI y nacimiento", async () => {
    const user = userEvent.setup();
    const fetchPage = vi.fn(async () => ({
      results: [
        {
          public_id: "persona-1",
          first_name: "Ana",
          last_name: "Gomez",
          cui: "1234567890123",
          birth_date: "2001-05-20",
          email: "ana@example.test",
          address: "Zona 1",
        },
      ],
    }));
    const onSubmit = vi.fn();
    renderWithSession(
      <EntityFormWindow
        fields={[
          {
            ...existingPersonField,
            search: { ...existingPersonField.search, fetchPage },
          },
          { name: "first_name", label: "Nombres" },
          { name: "cui", label: "CUI" },
          { name: "birth_date", label: "Fecha de nacimiento" },
          { name: "address", label: "Dirección" },
        ]}
        initialValues={{
          person_public_id: "",
          first_name: "",
          cui: "",
          birth_date: "",
          address: "",
        }}
        onCancel={vi.fn()}
        onSubmit={onSubmit}
        open
        title="Nuevo registro"
      />,
      { user: sessionUser() }
    );

    await user.type(
      await screen.findByLabelText(/Persona ya registrada/),
      "Ana"
    );
    await user.click(await screen.findByText(/^Ana Gomez/));

    expect(screen.getByLabelText("Nombres")).toHaveValue("Ana");
    expect(screen.getByLabelText("Dirección")).toHaveValue("Zona 1");
    expect(screen.getByLabelText("CUI")).toHaveValue("");
    expect(screen.getByLabelText("Fecha de nacimiento")).toHaveValue("");

    await user.click(screen.getByRole("button", { name: "Guardar" }));
    // Solo se escriben los campos del formulario: el correo no viaja.
    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({
        person_public_id: "persona-1",
        first_name: "Ana",
        cui: "",
        birth_date: "",
        address: "Zona 1",
      })
    );
  });
});

describe("claves explicitas de catalogo (1.2.4)", () => {
  test("la key sale del nombre declarado, no de load.name", async () => {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = ({ children }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    // Dos funciones con el MISMO nombre (como tras minificar) no comparten cache.
    const loadA = defineCatalog("cycles", async function a() {
      return [{ value: "c", label: "ciclo" }];
    });
    const loadB = defineCatalog("sections", async function a() {
      return [{ value: "s", label: "seccion" }];
    });

    const first = renderHook(() => useCatalogOptions(loadA), { wrapper });
    const second = renderHook(() => useCatalogOptions(loadB), { wrapper });

    await waitFor(() =>
      expect(first.result.current.options[0].value).toBe("c")
    );
    await waitFor(() =>
      expect(second.result.current.options[0].value).toBe("s")
    );
    const keys = client
      .getQueryCache()
      .getAll()
      .map((query) => query.queryKey);
    expect(keys).toEqual(
      expect.arrayContaining([
        ["catalog", "cycles", 0],
        ["catalog", "sections", 0],
      ])
    );
  });
});
