import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

const rolesServiceMock = vi.hoisted(() => ({
  listPage: vi.fn(),
  listAll: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  deactivate: vi.fn(),
  reactivate: vi.fn(),
  holders: vi.fn(),
  permissions: vi.fn(),
  permissionHolders: vi.fn(),
  scopeOptions: vi.fn(),
}));
vi.mock("@auth/rolesService.js", async (importOriginal) => ({
  ...(await importOriginal()),
  rolesService: rolesServiceMock,
}));
const accountsServiceMock = vi.hoisted(() => ({ assignRole: vi.fn() }));
vi.mock("@auth/accountsService.js", async (importOriginal) => ({
  ...(await importOriginal()),
  accountsService: accountsServiceMock,
}));
vi.mock("@shared/catalogs/academicCatalogs.js", async (importOriginal) => {
  const actual = await importOriginal();
  const catalog = (options) => () => ({ options, loading: false, error: "" });
  return {
    ...actual,
    useCycleCatalog: catalog([
      { value: "cy-1", label: "Ciclo 2027 · Activo", endsOn: "2027-10-31" },
    ]),
    useGradeCatalog: catalog([]),
    useSubjectCatalog: catalog([]),
    useSectionCatalog: catalog([
      { value: "sec-1", label: "Primero Básico A", cycleId: "cy-1" },
    ]),
  };
});

import { AssignRoleWizard } from "@auth/AssignRoleWizard.jsx";
import { RolesPage } from "@auth/RolesPage.jsx";
import { slugPreview } from "@auth/roleText.js";
import { scopePayload } from "@auth/scopeChoice.js";

import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";

const PERMISSIONS = [
  {
    code: "grade.write",
    name: "Registrar notas",
    description: "Permite registrar calificaciones.",
    group: "evaluation",
    group_label: "Evaluación",
  },
  {
    code: "grade.correct",
    name: "Corregir notas",
    description: "Permite corregir calificaciones.",
    group: "evaluation",
    group_label: "Evaluación",
  },
  {
    code: "audit.read",
    name: "Consultar la bitácora",
    description: "Permite consultar la bitácora.",
    group: "audit",
    group_label: "Auditoría",
  },
];
const ROLES = [
  {
    public_id: "r-1",
    name: "Docente",
    slug: "docente",
    description: "Registra notas de sus cursos.",
    is_system: false,
    is_active: true,
    session_idle_timeout_minutes: 60,
    active_account_count: 12,
    permissions: ["grade.write"],
  },
  {
    public_id: "r-2",
    name: "System Administrator",
    slug: "system-administrator",
    description: "",
    is_system: true,
    is_active: true,
    session_idle_timeout_minutes: 30,
    active_account_count: 1,
    permissions: ["audit.read", "grade.write", "grade.correct"],
  },
];
const ADMIN = sessionUser(["role.assign"]);

beforeEach(() => {
  Object.values(rolesServiceMock).forEach((fn) => fn.mockReset());
  rolesServiceMock.listPage.mockResolvedValue({ count: 2, results: ROLES });
  rolesServiceMock.listAll.mockResolvedValue(ROLES);
  rolesServiceMock.permissions.mockResolvedValue(PERMISSIONS);
  rolesServiceMock.scopeOptions.mockResolvedValue({
    modules: [
      { value: "students", label: "Expedientes de estudiantes" },
      {
        value: "teaching_assignments",
        label: "Sus asignaciones docentes vigentes",
      },
    ],
    institution: { public_id: "inst-1", name: "INEBI" },
  });
});

describe("RolesPage (RO1-RO6)", () => {
  test("lista cuentas por rol, marca los del sistema y oculta retirados por defecto", async () => {
    renderWithSession(<RolesPage />, { user: ADMIN, route: "/app/roles" });

    expect(await screen.findByText("Docente")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("Del sistema")).toBeInTheDocument();
    expect(rolesServiceMock.listPage).toHaveBeenCalledWith({
      page: 1,
      page_size: 50,
      include_inactive: "false",
    });
  });

  test("el editor agrupa permisos traducidos y explica que gana el mayor tiempo", async () => {
    const user = userEvent.setup();
    rolesServiceMock.create.mockResolvedValue({});
    renderWithSession(<RolesPage />, { user: ADMIN, route: "/app/roles" });
    await screen.findByText("Docente");

    await user.click(screen.getByRole("button", { name: "Nuevo rol" }));
    expect(await screen.findByText("Evaluación (0/2)")).toBeInTheDocument();
    expect(
      screen.getByText("Permite corregir calificaciones.")
    ).toBeInTheDocument();
    expect(screen.getByText(/gana el tiempo MAYOR/)).toBeInTheDocument();

    await user.type(screen.getByLabelText(/^Nombre/), "Coordinación Académica");
    expect(
      screen.getByText(/coordinacion-academica \(se genera del nombre\)/)
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("checkbox", { name: /Evaluación \(0\/2\)/ })
    );
    await user.click(screen.getByRole("button", { name: "Crear rol" }));

    await waitFor(() =>
      expect(rolesServiceMock.create).toHaveBeenCalledWith({
        name: "Coordinación Académica",
        description: "",
        session_idle_timeout_minutes: 30,
        permissions: ["grade.correct", "grade.write"],
      })
    );
  });

  test("un rol del sistema se muestra protegido para quien no es superusuario", async () => {
    const user = userEvent.setup();
    renderWithSession(<RolesPage />, { user: ADMIN, route: "/app/roles" });

    await user.click(await screen.findByText("System Administrator"));

    expect(await screen.findByText(/Rol del sistema/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Guardar cambios" })
    ).toBeDisabled();
  });

  test("retirar un rol exige motivo y no se ofrece para roles del sistema", async () => {
    const user = userEvent.setup();
    rolesServiceMock.deactivate.mockResolvedValue({});
    renderWithSession(<RolesPage />, { user: ADMIN, route: "/app/roles" });
    await screen.findByText("Docente");

    await user.click(
      screen.getByRole("button", { name: "Acciones de System Administrator" })
    );
    expect(
      within(await screen.findByRole("menu")).queryByText("Retirar rol")
    ).toBeNull();
    await user.keyboard("{Escape}");

    await user.click(
      screen.getByRole("button", { name: "Acciones de Docente" })
    );
    await user.click(await screen.findByText("Retirar rol"));
    await user.type(
      screen.getByLabelText(/Motivo/),
      "Fusionado con Docente titular"
    );
    await user.click(screen.getByRole("button", { name: "Retirar" }));

    expect(rolesServiceMock.deactivate).toHaveBeenCalledWith(
      "r-1",
      "Fusionado con Docente titular"
    );
  });

  test("compara roles por permiso", async () => {
    const user = userEvent.setup();
    renderWithSession(<RolesPage />, { user: ADMIN, route: "/app/roles" });
    await screen.findByText("Docente");

    await user.click(screen.getByRole("button", { name: "Comparar roles" }));

    const table = await screen.findByRole("table", {
      name: "Comparación de roles",
    });
    const row = within(table).getByText("Corregir notas").closest("tr");
    expect(within(row).getAllByText("—")).toHaveLength(1);
    expect(within(row).getAllByText("Sí")).toHaveLength(1);
  });

  test("slug derivado del nombre sin tildes", () => {
    expect(slugPreview("Coordinación  Académica")).toBe(
      "coordinacion-academica"
    );
  });
});

describe("AssignRoleWizard (RA1, RA3, RA4)", () => {
  const TEACHER = {
    public_id: "acc-1",
    username: "marta",
    person: { full_name: "Marta Xicará", is_teacher: true },
  };

  test("el alcance se envia por public_id y la vigencia sugiere el fin del ciclo", async () => {
    const user = userEvent.setup();
    accountsServiceMock.assignRole.mockResolvedValue({});
    const onClose = vi.fn();
    renderWithSession(
      <AssignRoleWizard account={TEACHER} onClose={onClose} open />,
      { user: ADMIN }
    );

    await user.click(await screen.findByLabelText("Rol"));
    await user.click(await screen.findByRole("option", { name: "Docente" }));
    expect(
      screen.getByText("Registra notas de sus cursos.")
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Siguiente" }));

    await user.click(screen.getByLabelText("Tipo de alcance"));
    await user.click(
      await screen.findByRole("option", { name: "Una sección" })
    );
    await user.click(screen.getByLabelText("Ciclo escolar"));
    await user.click(
      await screen.findByRole("option", { name: "Ciclo 2027 · Activo" })
    );
    await user.click(screen.getByLabelText("Sección"));
    await user.click(
      await screen.findByRole("option", { name: "Primero Básico A" })
    );
    await user.click(screen.getByRole("button", { name: "Siguiente" }));

    expect(screen.getByLabelText("Hasta")).toHaveValue("2027-10-31");
    expect(screen.getByText(/la sección Primero Básico A/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Asignar rol" }));

    await waitFor(() =>
      expect(accountsServiceMock.assignRole).toHaveBeenCalled()
    );
    const [accountId, payload] = accountsServiceMock.assignRole.mock.calls[0];
    expect(accountId).toBe("acc-1");
    expect(payload.role).toBe("r-1");
    expect(payload.scope).toEqual({ section: "sec-1", academic_cycle: "cy-1" });
    expect(payload.ends_at).toMatch(/^2027-1[01]-/);
    expect(onClose).toHaveBeenCalled();
  });

  test("ofrece 'Sus asignaciones docentes vigentes' solo a docentes", async () => {
    const user = userEvent.setup();
    renderWithSession(
      <AssignRoleWizard
        account={{
          ...TEACHER,
          person: { full_name: "Luis", is_teacher: false },
        }}
        onClose={vi.fn()}
        open
      />,
      { user: ADMIN }
    );
    await user.click(await screen.findByLabelText("Rol"));
    await user.click(await screen.findByRole("option", { name: "Docente" }));
    await user.click(screen.getByRole("button", { name: "Siguiente" }));
    await user.click(screen.getByLabelText("Tipo de alcance"));

    const listbox = await screen.findByRole("listbox");
    expect(
      within(listbox).queryByRole("option", {
        name: "Sus asignaciones docentes vigentes",
      })
    ).toBeNull();
    expect(
      within(listbox).getByRole("option", { name: "Toda la institución" })
    ).toBeInTheDocument();
  });

  test("traduce cada eleccion al contrato de alcance", () => {
    expect(scopePayload({ type: "teaching_assignments" })).toEqual({
      teaching_assignments: true,
    });
    expect(
      scopePayload({ type: "institution" }, { institution: { public_id: "i" } })
    ).toEqual({ institution: "i" });
    expect(scopePayload({ type: "module", value: "students" })).toEqual({
      module_key: "students",
    });
    expect(scopePayload({ type: "grade", value: "" })).toBeNull();
  });
});
