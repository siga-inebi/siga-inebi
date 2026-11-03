/**
 * Máximo de estudiantes por exportación de carnés (RF-CRE-002); el backend
 * rechaza más. Vive fuera de `attendanceService.js` para que el listado de
 * estudiantes lo use sin descargar el servicio de asistencia completo.
 */
export const CARD_EXPORT_LIMIT = 100;
