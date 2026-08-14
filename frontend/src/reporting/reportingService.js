import { apiClient } from "@shared/api/apiClient.js";
import { withQuery } from "@shared/api/query.js";

const ROOT = "/reporting";

/** Tipos de alerta institucional. */
export const ALERT_LABEL = {
  ausente_sin_registro: "Ausente sin registro",
  permanencia_sin_cierre: "Permanencia sin cierre",
  frecuencia_ausencias: "Frecuencia de ausencias",
  inconsistencia: "Inconsistencia",
};

export const ALERT_VARIANT = {
  ausente_sin_registro: "danger",
  permanencia_sin_cierre: "warning",
  frecuencia_ausencias: "purple",
  inconsistencia: "danger",
};

export const ALERT_TYPE_OPTIONS = Object.entries(ALERT_LABEL).map(([value, label]) => ({
  value,
  label,
}));

export const reportingService = {
  /**
   * Alertas institucionales. Todos los filtros son opcionales: sin parametros
   * devuelve el tablero completo.
   *
   * `dropFalse: false` porque aqui `false` SI es significativo: `?acknowledged=false`
   * es justamente la consulta util (lo que falta atender), no un filtro apagado.
   */
  listAlerts: (params) =>
    apiClient.get(withQuery(`${ROOT}/alerts/`, params, { dropFalse: false })),

  acknowledge: (publicId) => apiClient.post(`${ROOT}/alerts/${publicId}/acknowledge/`, {}),

  /** Recalculo de alertas de una jornada y fecha. */
  evaluate: (payload) => apiClient.post(`${ROOT}/alert-evaluations/`, payload),

  /** Umbrales de ausencia por jornada y ciclo. */
  listAbsenceThresholds: (params) =>
    apiClient.get(withQuery(`${ROOT}/absence-threshold-parameters/`, params)),
  createAbsenceThreshold: (payload) =>
    apiClient.post(`${ROOT}/absence-threshold-parameters/`, payload),
};
