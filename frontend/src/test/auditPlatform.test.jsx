import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

const auditServiceMock = vi.hoisted(() => ({
  events: vi.fn(),
  exportEvents: vi.fn(),
  declareRetention: vi.fn(),
  retentionDeclarations: vi.fn(),
}));
vi.mock("@audit/auditService.js", async (importOriginal) => ({
  ...(await importOriginal()),
  auditService: auditServiceMock,
}));
const platformServiceMock = vi.hoisted(() => ({
  taskRuns: vi.fn(),
  taskHealth: vi.fn(),
  backupHealth: vi.fn(),
  apiHealth: vi.fn(),
  databaseHealth: vi.fn(),
}));
vi.mock("@platform/platformService.js", async (importOriginal) => ({
  ...(await importOriginal()),
  platformService: platformServiceMock,
}));
const downloadMock = vi.hoisted(() => ({ downloadBlob: vi.fn() }));
vi.mock("@shared/utils/download.js", async (importOriginal) => ({
  ...(await importOriginal()),
  downloadBlob: downloadMock.downloadBlob,
}));

import { AuditPage } from "@audit/AuditPage.jsx";
import { PlatformPage } from "@platform/PlatformPage.jsx";

import {
  renderWithSession,
  sessionUser,
} from "./helpers/renderWithSession.jsx";

const EVENT = {
  public_id: "ev-1",
  actor_label: "ana.lopez",
  action: "identity.account.unlocked",
  resource: "UserAccount",
  resource_identifier: "7",
  ip_address: "10.0.0.2",
  context: { result: "success", reason: "Verificada en ventanilla" },
  created_at: "2026-10-17T15:00:00Z",
};

beforeEach(() => {
  Object.values(auditServiceMock).forEach((fn) => fn.mockReset());
  Object.values(platformServiceMock).forEach((fn) => fn.mockReset());
  auditServiceMock.events.mockResolvedValue({ count: 1, results: [EVENT] });
  auditServiceMock.retentionDeclarations.mockResolvedValue({
    count: 1,
    results: [
      {
        public_id: "ev-2",
        actor_label: "dpo",
        created_at: "2026-10-01T10:00:00Z",
        context: {
          category: "student.health_notes",
          period_days: 1825,
          legal_basis: "Reglamento interno",
          applies_to_minors: true,
        },
      },
    ],
  });
});

describe("AuditPage (AU1, AU2)", () => {
  test("lista asientos con etiquetas en español y abre el detalle con su contexto", async () => {
    const user = userEvent.setup();
    renderWithSession(<AuditPage />, {
      user: sessionUser(["audit.read"]),
      route: "/app/auditoria",
    });

    await user.click(await screen.findByText("Cuenta desbloqueada"));

    expect(await screen.findByText("Asiento de bitácora")).toBeInTheDocument();
    expect(
      screen.getAllByText("Verificada en ventanilla").length
    ).toBeGreaterThan(0);
  });

  test("filtra por tipo de accion en el servidor y exporta con los mismos filtros", async () => {
    const user = userEvent.setup();
    auditServiceMock.exportEvents.mockResolvedValue({
      blob: new Blob(["a"]),
      headers: new Headers({
        "Content-Disposition": 'attachment; filename="audit-events.csv"',
      }),
    });
    renderWithSession(<AuditPage />, {
      user: sessionUser(["audit.read"]),
      route: "/app/auditoria",
    });
    await screen.findByText("Cuenta desbloqueada");

    await user.click(screen.getByLabelText("Acción"));
    await user.click(
      within(await screen.findByRole("listbox")).getByRole("option", {
        name: "Cuentas",
      })
    );
    await waitFor(() =>
      expect(auditServiceMock.events).toHaveBeenLastCalledWith({
        page: 1,
        page_size: 25,
        action_prefix: "identity.account",
      })
    );

    await user.click(screen.getByRole("button", { name: "Exportar CSV" }));

    await waitFor(() =>
      expect(auditServiceMock.exportEvents).toHaveBeenCalledWith({
        action_prefix: "identity.account",
      })
    );
    expect(downloadMock.downloadBlob).toHaveBeenCalledWith(
      "audit-events.csv",
      expect.any(Blob)
    );
  });

  test("las declaraciones de retencion se listan y se declaran con permiso", async () => {
    const user = userEvent.setup();
    auditServiceMock.declareRetention.mockResolvedValue({});
    renderWithSession(<AuditPage />, {
      user: sessionUser(["audit.read", "retention_policy.declare"]),
      route: "/app/auditoria",
    });

    await user.click(
      await screen.findByRole("tab", { name: "Retención de datos" })
    );
    expect(await screen.findByText("student.health_notes")).toBeInTheDocument();
    expect(screen.getByText("1825 días")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Declarar plazo" }));
    await user.type(
      screen.getByLabelText(/Categoría de datos/),
      "documents.records"
    );
    await user.type(screen.getByLabelText(/Plazo de retención/), "3650");
    await user.type(
      screen.getByLabelText(/Justificación legal/),
      "Ley de archivos"
    );
    await user.click(screen.getByRole("button", { name: "Declarar" }));

    await waitFor(() =>
      expect(auditServiceMock.declareRetention).toHaveBeenCalledWith({
        category: "documents.records",
        period_days: 3650,
        legal_basis: "Ley de archivos",
        applies_to_minors: false,
      })
    );
  });

  test("sin audit.read solo se ofrece declarar plazos", async () => {
    renderWithSession(<AuditPage />, {
      user: sessionUser(["retention_policy.declare"]),
      route: "/app/auditoria",
    });

    expect(screen.queryByRole("tab", { name: "Bitácora" })).toBeNull();
    expect(
      screen.getByRole("button", { name: "Declarar plazo" })
    ).toBeInTheDocument();
    expect(auditServiceMock.events).not.toHaveBeenCalled();
  });
});

describe("PlatformPage (AU3)", () => {
  test("muestra salud de tareas, respaldos frente al RPO y servicio", async () => {
    platformServiceMock.apiHealth.mockResolvedValue({ status: "ok" });
    platformServiceMock.databaseHealth.mockResolvedValue({ status: "ok" });
    platformServiceMock.taskHealth.mockResolvedValue({
      count: 1,
      results: [
        {
          name: "evaluate_alerts",
          total_runs: 10,
          failed_runs: 2,
          running_runs: 0,
          last_started_at: "2026-10-17T06:00:00Z",
          last_finished_at: "2026-10-17T06:00:01Z",
          last_status: "failed",
          last_duration_ms: 1500,
          last_error_message: "Tiempo agotado",
        },
      ],
    });
    platformServiceMock.backupHealth.mockResolvedValue({
      count: 2,
      results: [
        {
          stack: "database",
          meets_rpo: true,
          created_at: "2026-10-17T02:00:00Z",
          age_hours: 5,
          rpo_hours: 24,
          size_bytes: 2048,
          backup_count: 3,
        },
        {
          stack: "files",
          meets_rpo: false,
          created_at: null,
          age_hours: null,
          rpo_hours: 24,
          size_bytes: null,
          backup_count: 0,
        },
      ],
    });
    platformServiceMock.taskRuns.mockResolvedValue({ count: 0, results: [] });
    renderWithSession(<PlatformPage />, {
      user: sessionUser(["platform.monitor"]),
      route: "/app/plataforma",
    });

    expect(
      (await screen.findAllByText("evaluate_alerts")).length
    ).toBeGreaterThan(0);
    expect(screen.getByText("Tiempo agotado")).toBeInTheDocument();
    expect(screen.getByText(/^1[.,]5 s$/)).toBeInTheDocument();
    expect(await screen.findByText("Dentro del RPO")).toBeInTheDocument();
    expect(screen.getByText("Fuera del RPO")).toBeInTheDocument();
    expect(screen.getAllByText("Base de datos").length).toBe(2);
    expect((await screen.findAllByText("Operativo")).length).toBe(2);
  });
});
