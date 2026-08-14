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

  listAlerts: (params) => apiClient.get(withQuery(`${ROOT}/alerts/`, params)),
};
