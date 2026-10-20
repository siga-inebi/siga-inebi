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
   * Nombre y vigencia que tomaria el ciclo de ese anio, sin crearlo.
   *
   * La regla del calendario guatemalteco vive en el backend
   * (`apps/academics/school_calendar.py`) y se consulta en vez de duplicarse
   * aca: dos copias de la misma regla en dos lenguajes es como se llega a que
   * el formulario muestre una fecha y el servidor guarde otra.
   */
  defaults: (year) => apiClient.get(withQuery(`${ROOT}/defaults/`, { year })),

  /**
   * Detalle historico: trae la estructura completa congelada del ciclo
   * (ofertas de grado, plan de estudios, asignaciones y matriculas).
   */
  get: (publicId) => apiClient.get(`${ROOT}/${publicId}/`),

  activate: (publicId) => apiClient.post(`${ROOT}/${publicId}/activate/`, {}),

  /**
   * Cierra un ciclo activo y congela sus resultados (RF-CIC-004). El backend
   * rechaza el cierre mientras haya unidades de evaluacion abiertas o una
   * ventana de recuperacion vigente, y devuelve el motivo.
   */
  close: (publicId) => apiClient.post(`${ROOT}/${publicId}/close/`, {}),

  /**
   * Clona la estructura academica de un ciclo hacia uno nuevo. Las asignaciones
   * docentes se copian solo si se piden: arrastrarlas por defecto reasignaria
   * personal que quizas ya no trabaja en el establecimiento.
   */
  clone: (publicId, payload) =>
    apiClient.post(`${ROOT}/${publicId}/clone/`, payload),

  /** Corrige nombre, fechas o descripcion. Solo en borrador (C3). */
  update: (publicId, payload) =>
    apiClient.patch(`${ROOT}/${publicId}/`, payload),

  /** Reabre un ciclo cerrado con motivo (RF-CIC-005, C6). */
  reopen: (publicId, reason) =>
    apiClient.post(`${ROOT}/${publicId}/reopen/`, { reason }),

  /** Devuelve un ciclo activo a borrador con motivo (D3, D6). */
  revertToDraft: (publicId, reason) =>
    apiClient.post(`${ROOT}/${publicId}/revert-to-draft/`, { reason }),

  /**
   * Que permite hoy el ciclo: faltantes para activar, bloqueos para volver a
   * borrador, pendientes para cerrar y el otro ciclo activo (C7, D1, D6).
   * La interfaz solo lo muestra; el backend vuelve a validar cada accion.
   */
  readiness: (publicId) => apiClient.get(`${ROOT}/${publicId}/readiness/`),

  // dias no computables (RF-JOR-010, C8)
  listNonComputableDays: (publicId, params) =>
    apiClient.get(
      withQuery(`${ROOT}/${publicId}/non-computable-days/`, params)
    ),
  declareNonComputableDay: (publicId, payload) =>
    apiClient.post(`${ROOT}/${publicId}/non-computable-days/`, payload),
  removeNonComputableDay: (dayId) =>
    apiClient.del(`/academics/non-computable-days/${dayId}/`),

  // asignaciones del ciclo (AD2, AD3)
  assignmentMatrix: (publicId, params) =>
    apiClient.get(withQuery(`${ROOT}/${publicId}/assignment-matrix/`, params)),
  cloneAssignmentsPreview: (publicId, sourceCycleId) =>
    apiClient.get(
      withQuery(`${ROOT}/${publicId}/teaching-assignments/clone-preview/`, {
        source_cycle_id: sourceCycleId,
      })
    ),
  /** `{starts_on?, items: [{section_id, subject_id, teacher_id}]}` -> `{created, failed}`. */
  createAssignmentsBatch: (publicId, payload) =>
    apiClient.post(`${ROOT}/${publicId}/teaching-assignments/batch/`, payload),

  // publicacion del horario (RF-HOR-009)
  schedulePublication: (publicId) =>
    apiClient.get(`${ROOT}/${publicId}/schedule-publication/`),
  publishSchedule: (publicId) =>
    apiClient.post(`${ROOT}/${publicId}/schedule-publication/`, {}),
  unpublishSchedule: (publicId) =>
    apiClient.del(`${ROOT}/${publicId}/schedule-publication/`),
};
