import { apiClient } from "@shared/api/apiClient.js";
import { withQuery } from "@shared/api/query.js";

import { PROFILE_LABEL } from "./accountLabels.js";

const ROOT = "/identity";

/**
 * Administracion de cuentas (docs/ux-ui.md 2.17.3). Las cuentas se direccionan
 * por `public_id`; ningun metodo recibe ni envia el id entero interno.
 */
export const accountsService = {
  list: (params) => apiClient.get(withQuery(`${ROOT}/accounts/list/`, params)),
  get: (accountId) => apiClient.get(`${ROOT}/accounts/${accountId}/`),
  update: (accountId, data) =>
    apiClient.patch(`${ROOT}/accounts/${accountId}/`, data),
  /** U1: alta por `person_public_id`; responde el codigo de activacion una sola vez. */
  provision: ({ personPublicId, username, email }) =>
    apiClient.post(`${ROOT}/accounts/`, {
      person_public_id: personPublicId,
      username,
      ...(email ? { email } : {}),
    }),
  candidates: (params) =>
    apiClient.get(withQuery(`${ROOT}/accounts/candidates/`, params)),
  suggestUsername: (personPublicId) =>
    apiClient.get(
      withQuery(`${ROOT}/accounts/username-suggestion/`, {
        person: personPublicId,
      })
    ),
  reissueActivation: (accountId) =>
    apiClient.post(`${ROOT}/accounts/${accountId}/activation-challenges/`, {}),
  reactivate: (accountId, reason) =>
    apiClient.post(`${ROOT}/accounts/${accountId}/reactivate/`, { reason }),
  unlock: (accountId, reason) =>
    apiClient.post(`${ROOT}/accounts/${accountId}/unlock/`, { reason }),
  disable: (accountId, { force = false, reason = "" } = {}) =>
    apiClient.post(`${ROOT}/accounts/${accountId}/disable/`, {
      force,
      reason,
    }),
  /** Riesgo A: cierra una sesion concreta de otra cuenta. */
  closeSession: (accountId, sessionId) =>
    apiClient.post(
      `${ROOT}/accounts/${accountId}/sessions/${sessionId}/close/`,
      {}
    ),
  closeSessions: (accountId) =>
    apiClient.post(`${ROOT}/accounts/${accountId}/sessions/close/`, {}),
  issuePasswordReset: (accountId) =>
    apiClient.post(`${ROOT}/accounts/${accountId}/password-resets/`, {}),
  assignments: (accountId, params) =>
    apiClient.get(
      withQuery(`${ROOT}/accounts/${accountId}/role-assignments/`, params)
    ),
  assignRole: (accountId, payload) =>
    apiClient.post(`${ROOT}/accounts/${accountId}/role-assignments/`, payload),
  revokeAssignment: (assignmentId) =>
    apiClient.del(`${ROOT}/role-assignments/${assignmentId}/`),
  expiringAssignments: (params) =>
    apiClient.get(withQuery(`${ROOT}/role-assignments/expiring/`, params)),
};

/** Enlace completo de restablecimiento que se entrega a la persona (U3). */
export function passwordResetLink(token, origin = window.location.origin) {
  return `${origin}/restablecer?token=${encodeURIComponent(token)}`;
}

/** Enlace de la pagina publica de activacion (U1). */
export function activationLink(origin = window.location.origin) {
  return `${origin}/activar`;
}

/** Una persona candidata como opcion del buscador (nombre · CUI · perfiles). */
export function candidateOption(person) {
  const profiles = (person.profiles ?? [])
    .map((profile) => PROFILE_LABEL[profile] ?? profile)
    .join(", ");
  return {
    value: person.public_id,
    label: [
      person.full_name,
      person.cui_hint && `CUI ${person.cui_hint}`,
      profiles,
    ]
      .filter(Boolean)
      .join(" · "),
    email: person.email,
    fullName: person.full_name,
  };
}
