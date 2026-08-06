import { apiClient } from "./apiClient.js";

const ROOT = "/students";

/**
 * Duplicado de `academicsService.withQuery`/`peopleService.withQuery` a
 * proposito: `students` se mantiene como dominio de frontend independiente,
 * mismo criterio que los servicios de backend (AGENTS.md #9).
 */
function withQuery(path, params) {
  const query = new URLSearchParams();

  for (const [key, value] of Object.entries(params || {})) {
    if (
      value === undefined ||
      value === null ||
      value === "" ||
      value === false
    ) {
      continue;
    }
    query.set(key, String(value));
  }

  const suffix = query.toString();
  return suffix ? `${path}?${suffix}` : path;
}

/**
 * Solo cubre lo que los paneles de contactos de emergencia y relacion
 * estudiante-encargado necesitan (RF-EXP-004, RF-EXP-005). No incluye
 * `Student`/`Guardian` CRUD: esas rutas siguen sin nivelar a `public_id` en
 * esta ronda, ver PR de esta serie para el detalle.
 */
export const studentsService = {
  // guardianes activos, para el selector de "vincular encargado existente"
  listGuardianOptions: () => apiClient.get(`${ROOT}/guardians/options/`),

  // contactos de emergencia: siempre anidados bajo su estudiante
  listEmergencyContacts: (studentId, params) =>
    apiClient.get(
      withQuery(`${ROOT}/${studentId}/emergency-contacts/`, params)
    ),
  createEmergencyContact: (studentId, payload) =>
    apiClient.post(`${ROOT}/${studentId}/emergency-contacts/`, payload),
  updateEmergencyContact: (contactId, payload) =>
    apiClient.patch(`${ROOT}/emergency-contacts/${contactId}/`, payload),
  deactivateEmergencyContact: (contactId) =>
    apiClient.del(`${ROOT}/emergency-contacts/${contactId}/`),

  // relacion estudiante-encargado: siempre anidada bajo su estudiante
  listStudentGuardianRelations: (studentId, params) =>
    apiClient.get(
      withQuery(`${ROOT}/${studentId}/guardian-relations/`, params)
    ),
  createStudentGuardianRelation: (studentId, payload) =>
    apiClient.post(`${ROOT}/${studentId}/guardian-relations/`, payload),
  updateStudentGuardianRelation: (relationId, payload) =>
    apiClient.patch(`${ROOT}/guardian-relations/${relationId}/`, payload),
  endStudentGuardianRelation: (relationId) =>
    apiClient.del(`${ROOT}/guardian-relations/${relationId}/`),
};
