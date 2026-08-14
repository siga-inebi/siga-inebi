import { apiClient } from "@shared/api/apiClient.js";
import { withQuery } from "@shared/api/query.js";

const ROOT = "/academics/cycles";

/** Estados de un ciclo escolar, tal como los expone el backend. */
export const CYCLE_STATUS = {
  draft: "draft",
  active: "active",
  closed: "closed",
};

export const CYCLE_STATUS_LABEL = {
  draft: "Borrador",
  active: "Activo",
  closed: "Cerrado",
};

/** Estado de dominio -> variante semantica de chip. */
export const CYCLE_STATUS_VARIANT = {
  draft: "neutral",
  active: "success",
  closed: "warning",
};

export const cyclesService = {
  list: (params) => apiClient.get(withQuery(`${ROOT}/`, params)),
  create: (payload) => apiClient.post(`${ROOT}/`, payload),

  /**
   * Detalle historico: trae la estructura completa congelada del ciclo
   * (ofertas de grado, plan de estudios, asignaciones y matriculas).
   */
  get: (publicId) => apiClient.get(`${ROOT}/${publicId}/`),

  activate: (publicId) => apiClient.post(`${ROOT}/${publicId}/activate/`, {}),

  /**
   * Clona la estructura academica de un ciclo hacia uno nuevo. Las asignaciones
   * docentes se copian solo si se piden: arrastrarlas por defecto reasignaria
   * personal que quizas ya no trabaja en el establecimiento.
   */
  clone: (publicId, payload) =>
    apiClient.post(`${ROOT}/${publicId}/clone/`, payload),
};
