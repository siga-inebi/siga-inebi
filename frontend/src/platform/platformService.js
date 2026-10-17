import { apiClient } from "@shared/api/apiClient.js";
import { withQuery } from "@shared/api/query.js";

/** Salud de la plataforma: tareas programadas y respaldos (docs/ux-ui.md AU3). */
export const platformService = {
  taskRuns: (params) =>
    apiClient.get(withQuery("/platform/task-runs/", params)),
  taskHealth: () =>
    apiClient.get(withQuery("/platform/task-health/", { page_size: 100 })),
  backupHealth: () => apiClient.get("/platform/backup-health/"),
  apiHealth: () => apiClient.get("/health/"),
  databaseHealth: () => apiClient.get("/health/database/"),
};

export const TASK_STATUS_LABEL = {
  running: "En ejecución",
  succeeded: "Finalizada",
  failed: "Fallida",
};

export const TASK_STATUS_VARIANT = {
  running: "primary",
  succeeded: "success",
  failed: "danger",
};

export const BACKUP_STACK_LABEL = {
  database: "Base de datos",
  files: "Archivos",
};

/** "1,5 MB" */
export function formatBytes(bytes) {
  if (bytes == null) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = Number(bytes);
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toLocaleString("es-GT", { maximumFractionDigits: 1 })} ${units[unit]}`;
}

/** "450 ms" / "3,2 s" */
export function formatDuration(ms) {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toLocaleString("es-GT", { maximumFractionDigits: 1 })} s`;
}
