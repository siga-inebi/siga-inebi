import { apiClient } from "./apiClient.js";

const ROOT = "/people";

/**
 * Personas institucionales. Por ahora la interfaz academica solo necesita
 * leerlas, para elegir a quien asignar como docente de un curso.
 */
export const peopleService = {
  listPeople: (params) => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params || {})) {
      if (value === undefined || value === null || value === "") {
        continue;
      }
      query.set(key, String(value));
    }
    const suffix = query.toString();
    return apiClient.get(suffix ? `${ROOT}/?${suffix}` : `${ROOT}/`);
  },
};
