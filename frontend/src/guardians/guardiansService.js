import { apiClient } from "@shared/api/apiClient.js";
import { collectAllPages } from "@shared/api/pages.js";
import { withQuery } from "@shared/api/query.js";

export const guardiansService = {
  /** Pagina cruda del listado, con su `count` total. */
  listPage: (params) =>
    apiClient.get(withQuery("/students/guardians/", params)),
  /**
   * Listado completo con los filtros dados, recorriendo todas las paginas.
   *
   * Solo para la exportacion CSV que la persona pide: GuardiansPage pide al
   * servidor unicamente la pagina visible (`listPage`).
   */
  list: (params = {}) =>
    collectAllPages((page) =>
      guardiansService.listPage({ ...params, ...page })
    ),
  linkedStudents: (id, params) =>
    apiClient.get(withQuery(`/students/guardians/${id}/students/`, params)),
  studentCandidates: (id, params) =>
    apiClient.get(
      withQuery(`/students/guardians/${id}/student-candidates/`, params)
    ),
  linkStudent: (id, payload) =>
    apiClient.post(`/students/guardians/${id}/students/`, payload),
  get: (id) => apiClient.get(`/students/guardians/${id}/`),
  create: (data) => apiClient.post("/students/guardians/", data),
  deactivate: (id) => apiClient.del(`/students/guardians/${id}/`),
  // GuardianSerializer intentionally rejects nested `person` writes on update
  // (see backend/apps/students/api/serializers.py), so name/email/phone
  // edits go to /people/<public_id>/ — Guardian has no other own field to patch.
  update: async (id, { person }) => {
    if (person) {
      const { public_id: personPublicId, ...personData } = person;
      await apiClient.patch(`/people/${personPublicId}/`, personData);
    }
    return guardiansService.get(id);
  },
};
