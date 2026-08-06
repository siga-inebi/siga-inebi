import { apiClient } from "./apiClient.js";

export const guardiansService = {
  // TODO(guardians-pagination): only returns page 1 (PAGE_SIZE=25 backend-side);
  // GuardiansPage's own client-side pagination assumes it has the full list.
  list: () =>
    apiClient.get("/students/guardians/").then((page) => page.results),
  get: (id) => apiClient.get(`/students/guardians/${id}/`),
  create: (data) => apiClient.post("/students/guardians/", data),
  // GuardianSerializer intentionally rejects nested `person` writes on update
  // (see backend/apps/students/api/serializers.py), so name/email/phone
  // edits go to /people/<id>/ — Guardian has no other own field to patch.
  update: async (id, { person }) => {
    if (person) {
      const { id: personId, ...personData } = person;
      await apiClient.patch(`/people/${personId}/`, personData);
    }
    return guardiansService.get(id);
  },
};
