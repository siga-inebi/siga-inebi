import { apiClient } from "@shared/api/apiClient.js";
import { withQuery } from "@shared/api/query.js";

const ROOT = "/documents";

/**
 * Color del chip por tipo de documento.
 *
 * No es un catalogo: los tipos viven en la base de datos y se administran desde
 * "Tipos de documento" (RNF-MAN-001). Esto solo decora los codigos que el
 * producto trae de fabrica; un tipo nuevo se dibuja en gris y funciona igual,
 * asi que agregar uno nunca obliga a tocar el frontend.
 */
export const TEMPLATE_KIND_VARIANT = {
  certificate: "primary",
  report: "purple",
  other: "neutral",
};

/** Closed emission uses; document kinds remain the institution's editable classification. */
export function templateIssuanceUseLabel(code) {
  return (
    {
      none: "Ninguna",
      enrolment_certificate: "Constancia de inscripción",
      study_certificate: "Certificado de estudios",
    }[code ?? "none"] ?? code
  );
}

/** Opciones de un select a partir del catalogo que devuelve el backend. */
export function templateKindOptions(kinds) {
  return kinds.map((kind) => ({ value: kind.code, label: kind.label }));
}

/** Busca la etiqueta visible de un codigo; cae al codigo si el tipo ya no esta. */
export function templateKindLabel(kinds, code) {
  return kinds.find((kind) => kind.code === code)?.label ?? code;
}

export const documentsService = {
  listStudentRecords: (id, params) =>
    apiClient.get(withQuery(`${ROOT}/students/${id}/records/`, params)),
  listTemplateIssuanceUses: () =>
    apiClient.get(`${ROOT}/templates/issuance-uses/`),
  /** Catalogo institucional de tipos de documento (RNF-MAN-001). */
  listTypes: (params) => apiClient.get(withQuery(`${ROOT}/types/`, params)),
  createType: (payload) => apiClient.post(`${ROOT}/types/`, payload),
  updateType: (publicId, payload) =>
    apiClient.patch(`${ROOT}/types/${publicId}/`, payload),
  /** Baja logica: el tipo queda inactivo y sigue listandose con include_inactive. */
  deactivateType: (publicId) => apiClient.del(`${ROOT}/types/${publicId}/`),

  listTemplates: (params) =>
    apiClient.get(withQuery(`${ROOT}/templates/`, params)),
  getTemplate: (publicId) => apiClient.get(`${ROOT}/templates/${publicId}/`),
  createTemplate: (payload) => apiClient.post(`${ROOT}/templates/`, payload),
  updateTemplate: (publicId, payload) =>
    apiClient.patch(`${ROOT}/templates/${publicId}/`, payload),
  /** Baja logica: la plantilla queda inactiva y sigue listandose con include_inactive. */
  deactivateTemplate: (publicId) =>
    apiClient.del(`${ROOT}/templates/${publicId}/`),

  /** Historial inmutable de versiones de una plantilla (RF-PLA-005). */
  listTemplateVersions: (publicId, params) =>
    apiClient.get(withQuery(`${ROOT}/templates/${publicId}/versions/`, params)),
  previewTemplate: (publicId, payload) =>
    apiClient.post(`${ROOT}/templates/${publicId}/preview/`, { payload }),

  listEnrolmentRecords: (enrolmentId, params) =>
    apiClient.get(
      withQuery(`${ROOT}/enrolments/${enrolmentId}/records/`, params)
    ),
  uploadRecord: (payload) => apiClient.post(`${ROOT}/records/`, payload),
  scanRecord: (payload) => apiClient.post(`${ROOT}/records/scan/`, payload),
  replaceRecord: (publicId, payload) =>
    apiClient.post(`${ROOT}/records/${publicId}/versions/`, payload),
  verifyRecord: (publicId) =>
    apiClient.post(`${ROOT}/records/${publicId}/verify/`),
  /**
   * Token breve y de un solo uso para descargar un adjunto (RF-DOC-005).
   * Responde `{ token, expires_at, download_url }`.
   */
  issueDownloadToken: (publicId) =>
    apiClient.post(`${ROOT}/records/${publicId}/download-tokens/`),

  /** Expediente documental del docente (RF-DOC-001). */
  listTeacherRecords: (teacherPublicId, params) =>
    apiClient.get(
      withQuery(`${ROOT}/teachers/${teacherPublicId}/records/`, params)
    ),
  uploadTeacherRecord: (teacherPublicId, payload) =>
    apiClient.post(`${ROOT}/teachers/${teacherPublicId}/records/`, payload),
  storageConsumption: () => apiClient.get(`${ROOT}/storage-consumption/`),

  /**
   * Catalogo cerrado de etiquetas dinamicas (RF-PLA-002/003).
   *
   * Las etiquetas sensibles quedan fuera por defecto: incluirlas es una decision
   * explicita de quien arma la plantilla, no el comportamiento normal.
   */
  listFieldTags: (params) =>
    apiClient.get(withQuery(`${ROOT}/field-tags/`, params)),

  /**
   * Elegibilidad para emitir documento oficial de una matricula (RF-MAT-006).
   *
   * Responde 200 con `{ eligible, blocking_document_codes }` incluso cuando esta
   * bloqueada: no es un error de la peticion, es el resultado de la consulta.
   */
  /**
   * Emision individual de constancia o certificado (RF-EMI-001).
   *
   * `documentType` es `enrolment_certificate` o `study_certificate`. Devuelve
   * `{ blob, headers }`: el PDF no se guarda en el servidor, asi que esta es la
   * unica copia; folio, codigo de verificacion y SHA-256 llegan en cabezales.
   */
  issueIndividualDocument: (enrolmentId, documentType) =>
    apiClient.postForFile(`${ROOT}/official-issuance/individual/`, {
      enrolment_id: enrolmentId,
      document_type: documentType,
    }),

  issuanceEligibility: (enrolmentId) =>
    apiClient.get(
      withQuery(`${ROOT}/official-issuance/eligibility/`, {
        enrolment_id: enrolmentId,
      })
    ),
};
