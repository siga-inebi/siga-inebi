import {
  act,
  renderHook,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, test, vi } from "vitest";

const accountsServiceMock = vi.hoisted(() => ({
  get: vi.fn(),
  assignments: vi.fn(),
  closeSession: vi.fn(),
  reactivate: vi.fn(),
  update: vi.fn(),
  expiringAssignments: vi.fn(),
  list: vi.fn(),
}));
vi.mock("@auth/accountsService.js", async (importOriginal) => ({
  ...(await importOriginal()),
  accountsService: accountsServiceMock,
}));

import { AccountDetailPage } from "@auth/AccountDetailPage.jsx";
import { AuthContext } from "@auth/context.js";
import { useAccountActions } from "@auth/useAccountActions.jsx";
import { apiClient } from "@shared/api/apiClient.js";
import { EntityFormWindow } from "@shared/crud/EntityFormWindow.jsx";
import {
  DRAFT_PREFIX,
  sanitizeDraft,
  useFormDraft,
} from "@shared/hooks/useFormDraft.js";
import {
  KEEP_ALIVE_INTERVAL_MS,
  useSessionKeepAlive,
} from "@shared/hooks/useSessionKeepAlive.js";

import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";

const ADMIN = sessionUser(
  ["account.update", "account.activate", "account.disable", "role.assign"],
  { public_id: "me-1" }
);

function account(overrides = {}) {
  return {
    public_id: "acc-1",
    username: "ana.lopez",
    email: "ana@example.test",
    status: "active",
    status_display: "Activa",
    person_name: "Ana López",
    person: { public_id: "p", full_name: "Ana López", is_teacher: false },
    roles: [],
    is_locked: false,
    date_joined: "2026-01-01T00:00:00Z",
    failed_login_attempts: 0,
    sessions: [
      {
        public_id: "s-1",
        device: "Chrome en Windows",
        ip_address: "10.1.2.3",
        started_at: "2026-10-17T14:00:00Z",
        last_activity_at: "2026-10-17T15:00:00Z",
        expires_at: "2026-10-17T16:00:00Z",
        is_current: false,
      },
    ],
    recent_activity: [],
    activation_expires_at: null,
    ...overrides,
  };
}

function renderDetail(detail = {}) {
  accountsServiceMock.get.mockResolvedValue(account(detail));
  accountsServiceMock.assignments.mockResolvedValue({ count: 0, results: [] });
  return renderWithSession(
    <Routes>
      <Route element={<AccountDetailPage />} path="/app/cuentas/:accountId" />
    </Routes>,
    { user: ADMIN, route: "/app/cuentas/acc-1" }
  );
}

beforeEach(() => {
  Object.values(accountsServiceMock).forEach((fn) => fn.mockReset());
  try {
    window.localStorage.clear();
  } catch {
    // sin almacenamiento
  }
});

describe("D1: editar cuenta exige account.update y nunca la propia", () => {
  function actionsFor(user, target) {
    const wrapper = ({ children }) => (
      <AuthContext.Provider value={{ user }}>{children}</AuthContext.Provider>
    );
    const { result } = renderHook(() => useAccountActions(), { wrapper });
    return result.current
      .actionsFor(target)
      .filter((action) => !action.hidden)
      .map((action) => action.key);
  }

  test("con account.update se ofrece editar otra cuenta", () => {
    expect(actionsFor(ADMIN, account())).toContain("edit");
  });

  test("account.create ya no basta", () => {
    expect(
      actionsFor(sessionUser(["account.create"]), account())
    ).not.toContain("edit");
  });

  test("no se ofrece editar la cuenta propia", () => {
    expect(actionsFor(ADMIN, account({ public_id: "me-1" }))).not.toContain(
      "edit"
    );
  });
});

describe("D4: una cuenta desactivada no recibe roles", () => {
  test("'Asignar rol' queda deshabilitado con la explicacion y se ofrece reactivar ahi mismo", async () => {
    const user = userEvent.setup();
    renderDetail({ status: "disabled", status_display: "Desactivada" });

    expect(
      await screen.findByText("Reactive la cuenta antes de asignarle roles.")
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Asignar rol" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Reactivar" }));

    expect(
      await screen.findByRole("heading", { name: "Reactivar cuenta" })
    ).toBeInTheDocument();
  });
});

describe("Riesgo A: sesiones con dispositivo, IP y cierre individual", () => {
  test("la ficha lista la sesion y administracion la cierra", async () => {
    const user = userEvent.setup();
    accountsServiceMock.closeSession.mockResolvedValue(null);
    renderDetail();

    const row = (await screen.findByText("Chrome en Windows")).closest("tr");
    expect(within(row).getByText("10.1.2.3")).toBeInTheDocument();
    await user.click(
      within(row).getByRole("button", { name: "Cerrar sesión" })
    );
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: "Cerrar sesión",
      })
    );

    await waitFor(() =>
      expect(accountsServiceMock.closeSession).toHaveBeenCalledWith(
        "acc-1",
        "s-1"
      )
    );
  });
});

describe("Riesgo D: escribir con cambios sin guardar mantiene la sesion", () => {
  test("como maximo una renovacion por minuto y solo si el formulario esta sucio", () => {
    let clock = 1_000_000;
    const send = vi.fn().mockResolvedValue(null);
    const { result, rerender } = renderHook(
      ({ dirty }) => useSessionKeepAlive(dirty, { now: () => clock, send }),
      { initialProps: { dirty: false } }
    );

    expect(result.current()).toBe(false);
    rerender({ dirty: true });
    expect(result.current()).toBe(true);
    clock += 30_000;
    expect(result.current()).toBe(false);
    clock += KEEP_ALIVE_INTERVAL_MS;
    expect(result.current()).toBe(true);
    expect(send).toHaveBeenCalledTimes(2);
  });

  test("EntityFormWindow renueva la sesion al escribir solo cuando hay cambios", async () => {
    const user = userEvent.setup();
    const post = vi.spyOn(apiClient, "post").mockResolvedValue(null);
    renderWithSession(
      <EntityFormWindow
        fields={[{ name: "name", label: "Nombre" }]}
        initialValues={{ name: "" }}
        onCancel={vi.fn()}
        onSubmit={vi.fn()}
        open
        title="Formulario"
      />,
      { user: ADMIN }
    );

    await user.type(screen.getByLabelText("Nombre"), "abc");

    const keepAlives = post.mock.calls.filter(
      ([path]) => path === "/auth/session/keep-alive/"
    );
    expect(keepAlives).toHaveLength(1);
  });
});

describe("Riesgo D: borradores locales", () => {
  const FIELDS = [
    { name: "name", label: "Nombre" },
    { name: "password", label: "Contraseña", type: "password" },
  ];

  function renderForm(props = {}) {
    return renderWithSession(
      <EntityFormWindow
        draftKey="prueba"
        fields={FIELDS}
        initialValues={{ name: "", password: "" }}
        onCancel={vi.fn()}
        onSubmit={vi.fn()}
        open
        title="Formulario largo"
        {...props}
      />,
      { user: ADMIN }
    );
  }

  test("guarda por cuenta y formulario, sin la contraseña", async () => {
    const user = userEvent.setup();
    renderForm();

    await user.type(screen.getByLabelText("Nombre"), "Borrador");
    await user.type(screen.getByLabelText("Contraseña"), "secreta");

    const stored = JSON.parse(
      window.localStorage.getItem(`${DRAFT_PREFIX}:me-1:prueba`)
    );
    expect(stored.values).toEqual({ name: "Borrador" });
  });

  test("ofrece recuperar el borrador al volver a abrir", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem(
      `${DRAFT_PREFIX}:me-1:prueba`,
      JSON.stringify({
        savedAt: "2026-10-17T10:00:00Z",
        values: { name: "Guardado" },
      })
    );
    renderForm();

    expect(screen.getByText(/Hay un borrador sin guardar/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Recuperar" }));

    expect(screen.getByLabelText("Nombre")).toHaveValue("Guardado");
  });

  test("se borra al guardar con exito", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(null);
    renderForm({ onSubmit });

    await user.type(screen.getByLabelText("Nombre"), "Listo");
    await user.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(
      window.localStorage.getItem(`${DRAFT_PREFIX}:me-1:prueba`)
    ).toBeNull();
  });

  test("cancelar con cambios pide confirmacion y descarta el borrador", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    renderForm({ onCancel });

    await user.type(screen.getByLabelText("Nombre"), "x");
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(onCancel).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Descartar cambios" }));

    expect(onCancel).toHaveBeenCalled();
    expect(
      window.localStorage.getItem(`${DRAFT_PREFIX}:me-1:prueba`)
    ).toBeNull();
  });

  test("sin draftKey no guarda nada (otras pantallas no cambian)", async () => {
    const user = userEvent.setup();
    renderForm({ draftKey: null });

    await user.type(screen.getByLabelText("Nombre"), "x");

    expect(window.localStorage.length).toBe(0);
  });

  test("nunca guarda secretos por nombre", () => {
    expect(
      sanitizeDraft({
        username: "a",
        new_password: "x",
        activation_code: "1",
        token: "t",
      })
    ).toEqual({ username: "a" });
  });

  test("tolera un almacenamiento que falla", () => {
    const original = Object.getOwnPropertyDescriptor(window, "localStorage");
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      get() {
        throw new Error("bloqueado");
      },
    });
    try {
      const { result } = renderHook(() => useFormDraft("x", { a: 1 }));
      act(() => result.current.clear());
      expect(result.current.pending).toBeNull();
    } finally {
      Object.defineProperty(window, "localStorage", original);
    }
  });
});
