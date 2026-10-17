export const API_URL = import.meta.env.VITE_API_URL || "/api/v1";

/**
 * Eventos de la capa HTTP. El cliente no conoce a react-query ni a la sesion:
 * solo avisa, y quien le interesa escucha.
 *
 * - `siga:mutation`: una escritura (POST/PATCH/PUT/DELETE) termino bien. La
 *   capa de cache invalida lo que esa escritura pudo cambiar (ux-ui 1.2.3:
 *   "toda mutacion invalida lo que muestra"), ver `invalidation.js`.
 * - `siga:api-activity`: el servidor respondio a una peticion autenticada, asi
 *   que la sesion se renovo alli. El aviso de sesion por vencer cuenta desde
 *   aqui (ux-ui L4).
 * - `siga:session-expired`: el servidor cerro la sesion por inactividad.
 */
export const MUTATION_EVENT = "siga:mutation";
export const API_ACTIVITY_EVENT = "siga:api-activity";
export const SESSION_EXPIRED_EVENT = "siga:session-expired";

const SAFE_METHODS = ["GET", "HEAD", "OPTIONS", "TRACE"];

function emit(name, detail) {
  window.dispatchEvent(new CustomEvent(name, { detail }));
}

function getErrorMessage(detail) {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return (
      detail.find((item) => typeof item === "string") ||
      "Solicitud no completada."
    );
  }

  if (detail && typeof detail === "object") {
    const nested =
      detail.non_field_errors || detail.detail || Object.values(detail)[0];
    return getErrorMessage(nested);
  }

  return "Solicitud no completada.";
}

async function parseResponse(response, { asFile = false, method, path } = {}) {
  const expired = response.headers.get("X-SIGA-Session-Expired") === "1";
  if (!expired) {
    emit(API_ACTIVITY_EVENT, { method, path, status: response.status });
  }
  if (response.ok && method && !SAFE_METHODS.includes(method)) {
    emit(MUTATION_EVENT, { method, path });
  }

  if (asFile && response.ok) {
    // Archivos generados (PDF): el cuerpo es binario y los metadatos de la
    // emision viajan en los cabezales, asi que se devuelven ambos.
    return { blob: await response.blob(), headers: response.headers };
  }
  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await response.json() : null;

  if (!response.ok) {
    if (expired) {
      emit(SESSION_EXPIRED_EVENT, { path });
    }
    // El backend responde de tres formas segun la capa que rechaza: la de
    // dominio manda `{error: {detail}}`, las vistas de permisos mandan
    // `{error: "texto"}` y DRF manda los errores por campo (`{campo: [...]}`).
    // Sin la segunda y la tercera, un 403 explicado o un campo invalido se leian
    // como "Solicitud no completada.", que no le dice a nadie que corregir.
    const detail = data?.error?.detail ?? data?.error ?? data?.detail ?? data;
    const message = getErrorMessage(detail);
    const error = new Error(message);
    error.status = response.status;
    error.payload = data;
    throw error;
  }

  return data;
}

function getCookie(name) {
  const value = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith(`${name}=`))
    ?.split("=")[1];
  return value ? decodeURIComponent(value) : "";
}

async function request(path, { asFile = false, accept, ...options } = {}) {
  const headers = new Headers(options.headers || {});
  headers.set(
    "Accept",
    accept ??
      (asFile ? "application/pdf, application/json" : "application/json")
  );

  const isFormData = options.body instanceof FormData;
  if (options.body && !isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const method = (options.method || "GET").toUpperCase();
  if (!SAFE_METHODS.includes(method)) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) {
      headers.set("X-CSRFToken", csrfToken);
    }
  }

  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      method,
      credentials: "include",
      headers,
      body: options.body
        ? isFormData
          ? options.body
          : JSON.stringify(options.body)
        : undefined,
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        "No se pudo conectar con el servidor. Verifica tu conexión y vuelve a intentarlo.",
        { cause: error }
      );
    }
    throw error;
  }

  return parseResponse(response, { asFile, method, path });
}

export const apiClient = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body }),
  patch: (path, body) => request(path, { method: "PATCH", body }),
  del: (path) => request(path, { method: "DELETE" }),
  /** POST que responde un archivo: devuelve `{ blob, headers }`. */
  postForFile: (path, body) =>
    request(path, { method: "POST", body, asFile: true }),
  /** GET que responde un archivo (CSV de exportacion): devuelve `{ blob, headers }`. */
  getFile: (path, accept = "text/csv, application/json") =>
    request(path, { asFile: true, accept }),
};
