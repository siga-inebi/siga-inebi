import { apiClient } from "@shared/api/apiClient.js";
import { withQuery } from "@shared/api/query.js";

const ROOT = "/academics";

export const evaluationService = {
  /** Configuracion global de evaluacion: el default de toda la institucion. */
  getGlobalConfig: () => apiClient.get(`${ROOT}/evaluation-config/`),
  updateGlobalConfig: (payload) =>
    apiClient.patch(`${ROOT}/evaluation-config/`, payload),

  /**
   * Configuracion de un ciclo concreto. Existe para poder desviarse del default
   * global en un ciclo sin cambiarlo para todos los demas.
   */
  getCycleConfig: (cyclePublicId) =>
    apiClient.get(`${ROOT}/cycles/${cyclePublicId}/evaluation-config/`),
  updateCycleConfig: (cyclePublicId, payload) =>
    apiClient.patch(
      `${ROOT}/cycles/${cyclePublicId}/evaluation-config/`,
      payload
    ),

  /** Unidades de evaluacion (bimestres, trimestres) del ciclo. */
  listUnits: (cyclePublicId, params) =>
    apiClient.get(
      withQuery(`${ROOT}/cycles/${cyclePublicId}/evaluation-units/`, params)
    ),
  createUnit: (cyclePublicId, payload) =>
    apiClient.post(
      `${ROOT}/cycles/${cyclePublicId}/evaluation-units/`,
      payload
    ),

  /** Ventana de recuperacion de una unidad. */
  updateRecoveryWindow: (cyclePublicId, unitPublicId, payload) =>
    apiClient.patch(
      `${ROOT}/cycles/${cyclePublicId}/evaluation-units/${unitPublicId}/recovery-window/`,
      payload
    ),

  /**
   * Permisos excepcionales de captura fuera de ventana.
   *
   * Se otorgan por curso y docente, con motivo y vencimiento obligatorios: es una
   * excepcion auditable, no un permiso permanente.
   */
  listCaptureExceptions: (cyclePublicId, unitPublicId, params) =>
    apiClient.get(
      withQuery(
        `${ROOT}/cycles/${cyclePublicId}/evaluation-units/${unitPublicId}/capture-exceptions/`,
        params
      )
    ),
  createCaptureException: (cyclePublicId, unitPublicId, payload) =>
    apiClient.post(
      `${ROOT}/cycles/${cyclePublicId}/evaluation-units/${unitPublicId}/capture-exceptions/`,
      payload
    ),

  /**
   * Notas de unidad (RF-CAL-001): la nota consolidada que el docente ya
   * calculo para un estudiante, una subarea y una unidad. Registrar de nuevo
   * la misma combinacion actualiza la nota existente.
   */
  listGrades: (cyclePublicId, unitPublicId, params) =>
    apiClient.get(
      withQuery(
        `${ROOT}/cycles/${cyclePublicId}/evaluation-units/${unitPublicId}/grades/`,
        params
      )
    ),
  registerGrade: (cyclePublicId, unitPublicId, payload) =>
    apiClient.post(
      `${ROOT}/cycles/${cyclePublicId}/evaluation-units/${unitPublicId}/grades/`,
      payload
    ),
};
