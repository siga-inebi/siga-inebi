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

/**
 * Motivo estable de un escaneo rechazado (`reason_code`). El servidor lo envia
 * junto al texto libre de `reason` para los rechazos que el operador debe
 * distinguir: fuera de la ventana operativa de la jornada (RF-JOR-001) o turno
 * de captura vencido (RF-AUT-005).
 */
export const SCAN_REJECTION_MESSAGE = {
  non_school_day:
    "El escaneo cae en un día no lectivo de la jornada y no se registró.",
  outside_operating_window:
    "El escaneo está fuera del horario de recepción de la jornada (antes de la apertura o después del cierre) y no se registró.",
  capture_batch_expired:
    "El turno de captura venció y se cerró. Abra un turno nuevo para seguir registrando.",
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

  /**
   * Motivos del registro manual (RF-ASI-012). Por omisión el backend lista
   * solo los vigentes: el alta de un movimiento `manual` exige uno.
   */
  listManualReasons: (params) =>
    apiClient.get(withQuery(`${ROOT}/manual-registration-reasons/`, params)),

  /** Turno de captura del operador (RF-ASI-009, RF-AUT-005). */
  currentCaptureBatch: () => apiClient.get(`${ROOT}/capture-batches/current/`),
  openCaptureBatch: () => apiClient.post(`${ROOT}/capture-batches/`, {}),
  confirmCaptureBatch: (batchId) =>
    apiClient.post(`${ROOT}/capture-batches/${batchId}/confirm/`, {}),

  /** Proporción de cierres por cobertura (RF-ASI-013). */
  coverageRatio: (params) =>
    apiClient.get(
      withQuery(`${ROOT}/section-closures/coverage-ratio/`, params)
    ),

  /**
   * Carné del estudiante (RF-CRE-001..004). La emisión responde el QR
   * (`qr_code`, PNG en base64); después, quien tiene
   * `attendance.credential.print` lo vuelve a pedir con `revealCardQr`, y cada
   * lectura queda auditada en el backend.
   */
  cardStatus: (studentId) =>
    apiClient.get(
      withQuery(`${ROOT}/credentials/status/`, { student_id: studentId })
    ),
  issueCard: (studentId) =>
    apiClient.post(`${ROOT}/credentials/`, { student_id: studentId }),
  cardPrintContent: (studentId) =>
    apiClient.get(
      withQuery(`${ROOT}/credentials/print-content/`, { student_id: studentId })
    ),
  revokeCard: (studentId, reason) =>
    apiClient.post(`${ROOT}/credentials/revoke/`, {
      student_id: studentId,
      reason,
    }),
  /** QR del carné vigente. Es POST para que el estudiante no quede en la URL. */
  revealCardQr: (studentId) =>
    apiClient.post(`${ROOT}/credentials/qr/`, { student_id: studentId }),
  /**
   * Exportación de carnés (1 a 100 estudiantes). `format` es `pdf` (un solo
   * archivo con todos), `zip` (un PNG por carné) o `png` (exactamente uno).
   * La vista previa no emite nada: dice qué carnés están listos, cuáles se
   * emitirán al confirmar y cuáles se omiten y por qué.
   */
  previewCardExport: (studentIds, format) =>
    apiClient.post(`${ROOT}/credentials/export/preview/`, {
      student_ids: studentIds,
      format,
    }),
  /** Emite los carnés que falten y responde el archivo: `{ blob, headers }`. */
  exportCards: (studentIds, format) =>
    apiClient.postForFile(
      `${ROOT}/credentials/export/`,
      { student_ids: studentIds, format },
      `${CARD_EXPORT_MIME[format] ?? "application/octet-stream"}, application/json`
    ),

  /** Justificaciones (RF-JUS-001..007). */
  listJustifications: (params) =>
    apiClient.get(withQuery(`${ROOT}/justifications/`, params)),
  getJustification: (id) => apiClient.get(`${ROOT}/justifications/${id}/`),
  createJustification: (payload) =>
    apiClient.post(`${ROOT}/justifications/`, payload),
  resolveJustification: (id, payload) =>
    apiClient.post(`${ROOT}/justifications/${id}/resolve/`, payload),
  listJustificationReasons: (params) =>
    apiClient.get(withQuery(`${ROOT}/justification-reasons/`, params)),
  /** Metadatos del adjunto; la lectura queda auditada (RF-JUS-007). */
  getJustificationAttachment: (id) =>
    apiClient.get(`${ROOT}/justifications/${id}/attachment/`),
  uploadJustificationAttachment: (id, file) => {
    const payload = new FormData();
    payload.set("file", file);
    return apiClient.post(`${ROOT}/justifications/${id}/attachment/`, payload);
  },

  /** Permisos de salida anticipada o ingreso tardío (RF-JUS-008). */
  listPermits: (params) => apiClient.get(withQuery(`${ROOT}/permits/`, params)),
  getPermit: (id) => apiClient.get(`${ROOT}/permits/${id}/`),
  createPermit: (payload) => apiClient.post(`${ROOT}/permits/`, payload),
  resolvePermit: (id, payload) =>
    apiClient.post(`${ROOT}/permits/${id}/resolve/`, payload),
};

/** Estado de una justificación o un permiso → variante del chip. */
export const REQUEST_STATUS_VARIANT = {
  pending: "warning",
  approved: "success",
  rejected: "danger",
};

/** Respaldo si el backend no trae `status_display`. */
export const JUSTIFICATION_STATUS_LABEL = {
  pending: "Pendiente",
  approved: "Aprobada",
  rejected: "Rechazada",
};

export const PERMIT_STATUS_LABEL = {
  pending: "Pendiente",
  approved: "Aprobado",
  rejected: "Rechazado",
};

export const SITUATION_TYPE_LABEL = {
  absence: "Inasistencia",
  late_arrival: "Llegada tardía",
};

export const PERMIT_TYPE_LABEL = {
  early_exit: "Salida anticipada",
  late_arrival: "Ingreso tardío",
};

export const CARD_STATUS_LABEL = {
  active: "Vigente",
  revoked: "Revocado",
  none: "Sin carné",
};

/** Tipo del archivo de cada formato de exportación de carnés. */
const CARD_EXPORT_MIME = {
  pdf: "application/pdf",
  png: "image/png",
  zip: "application/zip",
};

export const CARD_STATUS_VARIANT = {
  active: "success",
  revoked: "danger",
  none: "neutral",
};

/** Quita los campos vacíos opcionales: el backend rechaza un UUID "". */
export function withoutBlank(payload) {
  return Object.fromEntries(
    Object.entries(payload).filter(
      ([, value]) => value !== "" && value !== null && value !== undefined
    )
  );
}
