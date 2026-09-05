import { apiClient } from "@shared/api/apiClient.js";

const ROOT = "/identity";

function withQuery(path, params) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params || {})) {
    if (
      value === undefined ||
      value === null ||
      value === "" ||
      value === false
    )
      continue;
    query.set(key, String(value));
  }
  const suffix = query.toString();
  return suffix ? `${path}?${suffix}` : path;
}

export const accountsService = {
  list: (params) => apiClient.get(withQuery(`${ROOT}/accounts/list/`, params)),
  disable: (accountId, { force = false } = {}) =>
    apiClient.post(`${ROOT}/accounts/${accountId}/disable/`, { force }),
  closeSessions: (accountId) =>
    apiClient.post(`${ROOT}/accounts/${accountId}/sessions/close/`, {}),
};
