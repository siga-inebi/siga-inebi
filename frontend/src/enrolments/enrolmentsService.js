import { apiClient } from "@shared/api/apiClient.js";
import { withQuery } from "@shared/api/query.js";

const ROOT = "/enrolments";

/** Estados de una matricula, tal como los expone el backend. */
export const ENROLMENT_STATUS_LABEL = {
  active: "Activa",
  withdrawn: "Retirada",
  completed: "Completada",
  cancelled: "Anulada",
};

export const ENROLMENT_STATUS_VARIANT = {
  active: "success",
  withdrawn: "danger",
  completed: "primary",
  cancelled: "neutral",
};

/** Estados de un requisito documental (RF-MAT-005). */
export const DOCUMENT_STATUS_LABEL = {
  pending: "Pendiente",
  delivered: "Entregado",
};

export const DOCUMENT_STATUS_VARIANT = {
  pending: "warning",
  delivered: "success",
};

/** Tipos de movimiento que devuelve el historial institucional (RF-MOV-003). */
export const MOVEMENT_TYPE_LABEL = {
  section_change: "Cambio de seccion",
  transfer_in: "Traslado de ingreso",
  transfer_out: "Traslado de egreso",
  withdrawal: "Retiro",
};

export const MOVEMENT_TYPE_VARIANT = {
  section_change: "primary",
  transfer_in: "success",
  transfer_out: "warning",
  withdrawal: "danger",
};

/**
 * Matricula y su historial.
 *
 * `register` elige en el servidor entre primera matricula y reinscripcion.
 * Las rutas explicitas `matriculate` y `reenrol` se conservan para clientes y
 * flujos existentes; `create` sigue siendo el alta del registro base.
 */
export const enrolmentsService = {
  /** Matriculas vigentes. Filtrable por estudiante (RF-MAT-007). */
  listActive: (params) => apiClient.get(withQuery(`${ROOT}/active/`, params)),

  /** Historial completo de un estudiante, activas e inactivas (RF-MAT-008). */
  listHistory: (params) => apiClient.get(withQuery(`${ROOT}/history/`, params)),

  /** Movimientos inmutables, con fecha efectiva y fecha de registro separadas. */
  listMovements: (params) =>
    apiClient.get(withQuery(`${ROOT}/movements/`, params)),

  create: (payload) => apiClient.post(`${ROOT}/`, payload),
  /** Alta individual: el servidor decide matrícula o reinscripción (M6). */
  register: (payload) => apiClient.post(`${ROOT}/registrations/`, payload),
  matriculate: (payload) => apiClient.post(`${ROOT}/matriculations/`, payload),
  reenrol: (payload) => apiClient.post(`${ROOT}/re-enrolments/`, payload),

  /** Requisitos documentales de una matricula (RF-MAT-005). */
  listDocuments: (enrolmentId, params) =>
    apiClient.get(withQuery(`${ROOT}/${enrolmentId}/documents/`, params)),
  addDocument: (enrolmentId, payload) =>
    apiClient.post(`${ROOT}/${enrolmentId}/documents/`, payload),
};
