import { apiClient } from "@shared/api/apiClient.js";
import { collectAllPages } from "@shared/api/pages.js";
import { withQuery } from "@shared/api/query.js";

const ROOT = "/identity";

/** Roles, permisos atomicos y opciones de alcance (docs/ux-ui.md 2.17.4-2.17.5). */
export const rolesService = {
  listPage: (params) => apiClient.get(withQuery(`${ROOT}/roles/`, params)),
  /** Todos los roles: son pocos, y el editor y la comparacion los necesitan juntos. */
  listAll: (params = {}) =>
    collectAllPages((pageParams) =>
      rolesService.listPage({ ...params, ...pageParams })
    ),
  get: (roleId) => apiClient.get(`${ROOT}/roles/${roleId}/`),
  create: (data) => apiClient.post(`${ROOT}/roles/`, data),
  update: (roleId, data) => apiClient.patch(`${ROOT}/roles/${roleId}/`, data),
  deactivate: (roleId, reason) =>
    apiClient.post(`${ROOT}/roles/${roleId}/deactivate/`, { reason }),
  reactivate: (roleId, reason) =>
    apiClient.post(`${ROOT}/roles/${roleId}/reactivate/`, { reason }),
  holders: (roleId, params) =>
    apiClient.get(withQuery(`${ROOT}/roles/${roleId}/holders/`, params)),
  permissions: () =>
    collectAllPages((params) =>
      apiClient.get(withQuery(`${ROOT}/permissions/`, params))
    ),
  permissionHolders: (code, params) =>
    apiClient.get(
      withQuery(
        `${ROOT}/permissions/${encodeURIComponent(code)}/holders/`,
        params
      )
    ),
  scopeOptions: () => apiClient.get(`${ROOT}/scope-options/`),
};

/** Agrupa el catalogo por `group`, en el orden en que llega (RO1). */
export function groupPermissions(permissions) {
  const groups = new Map();
  for (const permission of permissions) {
    if (!groups.has(permission.group)) {
      groups.set(permission.group, {
        key: permission.group,
        label: permission.group_label,
        permissions: [],
      });
    }
    groups.get(permission.group).permissions.push(permission);
  }
  return [...groups.values()];
}
