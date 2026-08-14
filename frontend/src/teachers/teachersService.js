import { apiClient } from "@shared/api/apiClient.js";

export const teachersService = {
  // TODO(teachers-pagination): only returns page 1 (PAGE_SIZE=25 backend-side);
  // DocentesPage's own client-side pagination assumes it has the full list.
  list: () => apiClient.get("/teachers/").then((page) => page.results),
  get: (id) => apiClient.get(`/teachers/${id}/`),
  create: async ({ photo, ...data }) => {
    const created = await apiClient.post("/teachers/", data);
    if (!photo) {
      return created;
    }
    const formData = new FormData();
    formData.append("photo", photo);
    return apiClient.patch(`/teachers/${created.id}/`, formData);
  },
  // TeacherSerializer intentionally rejects nested `person` writes on update
  // (see backend/apps/teachers/api/serializers.py), so name/email/phone
  // edits go to /people/<id>/ while employee_code/specialty/position/photo
  // go to /teachers/<id>/ — the same two-endpoint split used by create.
  update: async (id, { photo, person, ...data }) => {
    if (person) {
      const { id: personId, ...personData } = person;
      await apiClient.patch(`/people/${personId}/`, personData);
    }
    if (Object.keys(data).length > 0) {
      await apiClient.patch(`/teachers/${id}/`, data);
    }
    if (photo) {
      const formData = new FormData();
      formData.append("photo", photo);
      await apiClient.patch(`/teachers/${id}/`, formData);
    }
    return teachersService.get(id);
  },
};
