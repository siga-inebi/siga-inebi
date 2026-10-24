import { apiClient } from "@shared/api/apiClient.js";
import { withQuery } from "@shared/api/query.js";

const ROOT = "/academics";

/** Estados de una unidad de evaluación, tal como los expone el backend. */
export const UNIT_STATUS_LABEL = {
  open: "Abierta",
  closed: "Cerrada",
};

/** Estado de dominio -> variante semántica de chip. */
export const UNIT_STATUS_VARIANT = {
  open: "success",
  closed: "neutral",
};

/** Condición de una subárea (RF-RES-003, RF-RES-005). */
export const SUBJECT_CONDITION_LABEL = {
  approved: "Aprobada",
  approved_by_recovery: "Aprobada por recuperación",
  failed: "Reprobada",
};

export const SUBJECT_CONDITION_VARIANT = {
  approved: "success",
  approved_by_recovery: "primary",
  failed: "danger",
};

const cycle = (cycleId) => `${ROOT}/cycles/${cycleId}`;
const unit = (cycleId, unitId) =>
  `${cycle(cycleId)}/evaluation-units/${unitId}`;
const enrolment = (cycleId, enrolmentId) =>
  `${cycle(cycleId)}/enrolments/${enrolmentId}`;

export const evaluationService = {
  /** Configuración global de evaluación: el default de toda la institución. */
  getGlobalConfig: () => apiClient.get(`${ROOT}/evaluation-config/`),
  updateGlobalConfig: (payload) =>
    apiClient.patch(`${ROOT}/evaluation-config/`, payload),

  /**
   * Configuración de un ciclo concreto. Existe para poder desviarse del default
   * global en un ciclo sin cambiarlo para todos los demás.
   */
  getCycleConfig: (cycleId) =>
    apiClient.get(`${cycle(cycleId)}/evaluation-config/`),
  updateCycleConfig: (cycleId, payload) =>
    apiClient.patch(`${cycle(cycleId)}/evaluation-config/`, payload),

  /**
   * Copia las unidades (con sus ventanas, trasladadas por la diferencia de
   * inicio) y el número de unidades a un ciclo en borrador sin unidades (V6).
   */
  cloneConfig: (cycleId, targetCycleId) =>
    apiClient.post(`${cycle(cycleId)}/evaluation-config/clone/`, {
      target_cycle: targetCycleId,
    }),

  /** Unidades de evaluación (bimestres, trimestres) del ciclo. */
  listUnits: (cycleId, params) =>
    apiClient.get(withQuery(`${cycle(cycleId)}/evaluation-units/`, params)),
  createUnit: (cycleId, payload) =>
    apiClient.post(`${cycle(cycleId)}/evaluation-units/`, payload),
  /** Cierra la unidad (V1): ya no admite captura y habilita cerrar el ciclo. */
  closeUnit: (cycleId, unitId) =>
    apiClient.patch(`${unit(cycleId, unitId)}/close/`, {}),

  /** Ventana de recuperación de una unidad. */
  updateRecoveryWindow: (cycleId, unitId, payload) =>
    apiClient.patch(`${unit(cycleId, unitId)}/recovery-window/`, payload),

  /**
   * Permisos excepcionales de captura fuera de ventana (RF-EVC-004). Se
   * otorgan por subárea y docente, con motivo y vencimiento obligatorios.
   */
  listCaptureExceptions: (cycleId, unitId, params) =>
    apiClient.get(
      withQuery(`${unit(cycleId, unitId)}/capture-exceptions/`, params)
    ),
  createCaptureException: (cycleId, unitId, payload) =>
    apiClient.post(`${unit(cycleId, unitId)}/capture-exceptions/`, payload),

  /**
   * Planilla de una unidad, sección y subárea (V2, V8): una fila por matrícula
   * activa, la nota vigente y el docente de la asignación vigente.
   */
  getSheet: (cycleId, unitId, sectionId, subjectId) =>
    apiClient.get(
      withQuery(`${unit(cycleId, unitId)}/sheet/`, {
        section_id: sectionId,
        subject_id: subjectId,
      })
    ),
  /**
   * Guarda la planilla en un solo lote, todo o nada:
   * `{section_id, subject_id, grades: [{enrolment_id, value}]}` -> `{created, updated}`.
   * Un 400 por fila trae `payload.errors[].index` (en el orden enviado).
   */
  saveSheet: (cycleId, unitId, payload) =>
    apiClient.post(`${unit(cycleId, unitId)}/grades/sheet/`, payload),

  /**
   * Cursos (sección y subárea) que la cuenta puede calificar en el ciclo.
   * Dirección ve todos los del plan; un docente, solo sus asignaciones.
   */
  listGradeCourses: (cycleId) =>
    apiClient.get(`${ROOT}/cycles/${cycleId}/grade-courses/`),

  /**
   * Plantilla Excel del curso con todas las unidades del ciclo: devuelve
   * `{ blob, headers }` para descargarla con el nombre que manda el servidor.
   */
  downloadCourseWorkbook: (cycleId, sectionId, subjectId) =>
    apiClient.getFile(
      withQuery(`${ROOT}/cycles/${cycleId}/grade-workbook/`, {
        section_id: sectionId,
        subject_id: subjectId,
      }),
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/json"
    ),

  /**
   * Importa la plantilla del curso, todo o nada: `{created, updated, unchanged}`
   * o un 400 con `payload.errors[] = {row, student_code, unit, message}`.
   */
  importCourseWorkbook: (cycleId, sectionId, subjectId, file) => {
    const form = new FormData();
    form.append("file", file);
    form.append("section_id", sectionId);
    form.append("subject_id", subjectId);
    return apiClient.post(
      `${ROOT}/cycles/${cycleId}/grade-workbook/import/`,
      form
    );
  },

  /**
   * Datos del informe de calificaciones con los promedios ya calculados por el
   * backend. Sin filtros es todo el ciclo; `grade_id` (y `section_id`) o
   * `student_id` lo acotan.
   */
  getGradeReport: (cycleId, params) =>
    apiClient.get(withQuery(`${ROOT}/cycles/${cycleId}/grade-report/`, params)),

  /** Avance de captura de la unidad por sección y subárea (RF-CAL-008, V3). */
  getCaptureProgress: (cycleId, unitId) =>
    apiClient.get(`${unit(cycleId, unitId)}/capture-progress/`),

  /** Elegibilidad de recuperación de toda una sección, paginada (V4). */
  listSectionRecovery: (cycleId, sectionId, params) =>
    apiClient.get(
      withQuery(
        `${cycle(cycleId)}/sections/${sectionId}/recovery-eligibility/`,
        params
      )
    ),
  /** `{subject, value}`: nota de recuperación de una subárea reprobada. */
  registerRecoveryGrade: (cycleId, enrolmentId, payload) =>
    apiClient.post(
      `${enrolment(cycleId, enrolmentId)}/recovery-grades/`,
      payload
    ),

  /** Boleta: notas de unidad de una matrícula, con nombres de subárea. */
  getReportCard: (cycleId, enrolmentId) =>
    apiClient.get(`${enrolment(cycleId, enrolmentId)}/grades/`),

  /**
   * Nota final de una subárea (RF-RES-001): promedio de las unidades con nota,
   * redondeado por el sistema; una unidad sin nota no cuenta como cero.
   */
  getFinalSubjectGrade: (cycleId, enrolmentId, subjectId) =>
    apiClient.get(
      `${enrolment(cycleId, enrolmentId)}/subjects/${subjectId}/final-grade/`
    ),

  /** Resultados congelados al cierre del ciclo (RF-RES-007, V5). */
  listFrozenResults: (cycleId, enrolmentId) =>
    apiClient.get(`${enrolment(cycleId, enrolmentId)}/frozen-results/`),
  getFrozenPromotion: (cycleId, enrolmentId) =>
    apiClient.get(`${enrolment(cycleId, enrolmentId)}/frozen-promotion/`),
  /** Corrección auditada con motivo: `{final_grade, reason}`. */
  correctFrozenResult: (cycleId, enrolmentId, subjectId, payload) =>
    apiClient.post(
      `${enrolment(cycleId, enrolmentId)}/subjects/${subjectId}/frozen-result/correct/`,
      payload
    ),

  /** Trazabilidad del resultado de una subárea (RF-RES-009). */
  getResultTrace: (enrolmentId, subjectId) =>
    apiClient.get(
      `/audit/enrolments/${enrolmentId}/subjects/${subjectId}/result-trace/`
    ),
};
