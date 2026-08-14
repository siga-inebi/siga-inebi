import { apiClient } from "@shared/api/apiClient.js";
import { withQuery } from "@shared/api/query.js";

const ROOT = "/documents";

/** Tipos de plantilla documental. */
export const TEMPLATE_KIND_LABEL = {
  certificate: "Constancia",
  report: "Reporte",
  other: "Otro",
};

export const TEMPLATE_KIND_VARIANT = {
  certificate: "primary",
  report: "purple",
  other: "neutral",
};

export const TEMPLATE_KIND_OPTIONS = Object.entries(TEMPLATE_KIND_LABEL).map(
  ([value, label]) => ({ value, label })
);

export const documentsService = {
  listTemplates: (params) => apiClient.get(withQuery(`${ROOT}/templates/`, params)),
  getTemplate: (publicId) => apiClient.get(`${ROOT}/templates/${publicId}/`),
  createTemplate: (payload) => apiClient.post(`${ROOT}/templates/`, payload),
  updateTemplate: (publicId, payload) =>
    apiClient.patch(`${ROOT}/templates/${publicId}/`, payload),
  /** Baja logica: la plantilla queda inactiva y sigue listandose con include_inactive. */
  deactivateTemplate: (publicId) => apiClient.del(`${ROOT}/templates/${publicId}/`),

  /** Historial inmutable de versiones de una plantilla (RF-PLA-005). */
  listTemplateVersions: (publicId, params) =>
    apiClient.get(withQuery(`${ROOT}/templates/${publicId}/versions/`, params)),

  /**
   * Catalogo cerrado de etiquetas dinamicas (RF-PLA-002/003).
   *
   * Las etiquetas sensibles quedan fuera por defecto: incluirlas es una decision
   * explicita de quien arma la plantilla, no el comportamiento normal.
   */
  listFieldTags: (params) => apiClient.get(withQuery(`${ROOT}/field-tags/`, params)),

  /**
   * Elegibilidad para emitir documento oficial de una matricula (RF-MAT-006).
   *
   * Responde 200 con `{ eligible, blocking_document_codes }` incluso cuando esta
   * bloqueada: no es un error de la peticion, es el resultado de la consulta.
   */
  issuanceEligibility: (enrolmentId) =>
    apiClient.get(
      withQuery(`${ROOT}/official-issuance/eligibility/`, { enrolment_id: enrolmentId })
    ),
};
