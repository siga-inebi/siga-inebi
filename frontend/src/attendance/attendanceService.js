import { apiClient } from "@shared/api/apiClient.js";
import { withQuery } from "@shared/api/query.js";

const ROOT = "/attendance";

export const MOVEMENT_LABEL = { entry: "Entrada", exit: "Salida" };
export const MOVEMENT_VARIANT = { entry: "success", exit: "primary" };

export const ORIGIN_LABEL = {
  scan: "Lectura",
  manual: "Manual",
  declared: "Declarada",
};

export const ORIGIN_VARIANT = {
  scan: "primary",
  manual: "warning",
  declared: "purple",
};

export const TRANSMISSION_LABEL = { individual: "Individual", batch: "Lote" };

/** Resultado de un intento de captura por escaneo (RF-ASI-002/004/010). */
export const SCAN_OUTCOME_LABEL = {
  created: "Registrado",
  duplicate_suppressed: "Ya estaba registrado",
  already_processed: "Ya procesado",
  rejected: "Rechazado",
};

export const SCAN_OUTCOME_VARIANT = {
  created: "success",
  duplicate_suppressed: "warning",
  already_processed: "neutral",
  rejected: "danger",
};

/** Tipos de alerta que emite el modulo de asistencia. */
export const ATTENDANCE_ALERT_LABEL = {
  permanencia_sin_cierre: "Permanencia sin cierre",
  inconsistencia: "Inconsistencia",
};

export const ATTENDANCE_ALERT_VARIANT = {
  permanencia_sin_cierre: "warning",
  inconsistencia: "danger",
};

export const attendanceService = {
  /** Parametros de jornada vigentes por sede y ciclo (RF-JOR-001). */
  listJornadaParameters: (params) =>
    apiClient.get(withQuery(`${ROOT}/jornada-parameters/`, params)),
  createJornadaParameters: (payload) =>
    apiClient.post(`${ROOT}/jornada-parameters/`, payload),

  listEvents: (params) => apiClient.get(withQuery(`${ROOT}/events/`, params)),
  createEvent: (payload) => apiClient.post(`${ROOT}/events/`, payload),

  /**
   * Resolucion de un movimiento concreto. Exige los cuatro parametros
   * (`student_id`, `shift_id`, `event_date`, `movement_type`): responde cual de
   * los eventos duplicados quedo como valido tras la supresion.
   */
  eventResolution: (params) =>
    apiClient.get(withQuery(`${ROOT}/events/resolution/`, params)),

  /**
   * Estado del dia de un estudiante en una jornada. Los tres parametros son
   * obligatorios; sin ellos el backend responde 400.
   */
  dayStatus: (params) =>
    apiClient.get(withQuery(`${ROOT}/day-status/`, params)),

  /** Cierre de jornada: recalcula estados y emite alertas (RF-JOR-004/005). */
  closeJornada: (payload) =>
    apiClient.post(`${ROOT}/jornada-closures/`, payload),

  /** Previsualizacion y cierre declarado por seccion (RF-ASI-011/013). */
  previewSectionClosure: (params) =>
    apiClient.get(withQuery(`${ROOT}/section-closures/preview/`, params)),
  closeSection: (payload) =>
    apiClient.post(`${ROOT}/section-closures/`, payload),

  listAlerts: (params) => apiClient.get(withQuery(`${ROOT}/alerts/`, params)),

  /** Catalogo de puntos de control; alta por Django admin (RF-ASI-002). */
  listControlPoints: (params) =>
    apiClient.get(withQuery(`${ROOT}/control-points/`, params)),

  /**
   * Captura por escaneo (RF-ASI-001/002/004/010). El cuerpo lleva `items`
   * (uno o varios) y responde un arreglo con el resultado de cada uno, en el
   * mismo orden: `created`, `duplicate_suppressed`, `already_processed` o
   * `rejected`. No esta paginado: es la respuesta de una escritura, no un
   * listado.
   */
  recordScan: (payload) => apiClient.post(`${ROOT}/scan/`, payload),

  /**
   * Estudiantes con ingreso registrado y sin egreso, en tiempo real
   * (RF-JOR-008). `shift_id` es obligatorio; `event_date`, `grade_id` y
   * `section_id` son filtros opcionales.
   */
  listPresence: (params) =>
    apiClient.get(withQuery(`${ROOT}/presence/`, params)),

  /**
   * Porcentaje de asistencia de un estudiante sobre los dias lectivos ya
   * transcurridos en el ciclo (RF-JOR-009). Consulta puntual, un estudiante a
   * la vez.
   */
  attendancePercentage: (params) =>
    apiClient.get(withQuery(`${ROOT}/attendance-percentage/`, params)),
};
