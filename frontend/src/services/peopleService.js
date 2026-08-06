import { apiClient } from "./apiClient.js";

const ROOT = "/people";

/**
 * Builds the query string the people endpoints understand. Empty values are
 * dropped so `?page=1` never becomes `?page=1&include_inactive=false`.
 *
 * Duplicated from `academicsService.js` on purpose instead of imported:
 * `people` and `academics` stay independent frontend domains, same reasoning
 * as the backend services (AGENTS.md #9).
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
 * Personas institucionales: CRUD plano contra `/people/`. `del` es baja
 * logica (`is_active=false`): el registro sigue listandose con
 * `include_inactive=true`, igual que en `academicsService`.
 */
export const peopleService = {
  listPeople: (params) => apiClient.get(withQuery(`${ROOT}/`, params)),
  getPerson: (personId) => apiClient.get(`${ROOT}/${personId}/`),
  createPerson: (payload) => apiClient.post(`${ROOT}/`, payload),
  updatePerson: (personId, payload) =>
    apiClient.patch(`${ROOT}/${personId}/`, payload),
  deactivatePerson: (personId) => apiClient.del(`${ROOT}/${personId}/`),
};
