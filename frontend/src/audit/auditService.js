import { apiClient } from "@shared/api/apiClient.js";
import { withQuery } from "@shared/api/query.js";

/** Accion con la que el backend registra una declaracion de retencion (RNF-LEG-001). */
export const RETENTION_ACTION = "compliance.retention.declared";

/** Bitacora de auditoria y declaraciones de retencion (docs/ux-ui.md AU1, AU2). */
export const auditService = {
  events: (params) => apiClient.get(withQuery("/audit/events/", params)),
  /** CSV completo del rango filtrado, generado por el backend (sin truncar). */
  exportEvents: (params) =>
    apiClient.getFile(withQuery("/audit/events/export/", params)),
  declareRetention: (data) =>
    apiClient.post("/audit/retention-declarations/", data),
  retentionDeclarations: (params) =>
    apiClient.get(
      withQuery("/audit/events/", { ...params, action: RETENTION_ACTION })
    ),
};

/** Prefijos de accion que la consola ofrece como filtro. */
export const ACTION_PREFIX_OPTIONS = [
  { value: "identity.", label: "Identidad y accesos" },
  { value: "identity.login", label: "Inicios de sesión" },
  { value: "identity.account", label: "Cuentas" },
  { value: "identity.role", label: "Roles y asignaciones" },
  { value: "identity.authorization.denied", label: "Accesos denegados" },
  { value: "people.", label: "Personas" },
  { value: "students.", label: "Estudiantes" },
  { value: "teachers.", label: "Docentes" },
  { value: "enrolments.", label: "Matrícula" },
  { value: "attendance.", label: "Asistencia" },
  { value: "evaluation.", label: "Evaluación" },
  { value: "academics.", label: "Estructura académica" },
  { value: "documents.", label: "Documentos" },
  { value: "reporting.", label: "Alertas" },
  { value: "audit.", label: "Consultas de auditoría" },
  { value: "compliance.", label: "Cumplimiento y retención" },
];
