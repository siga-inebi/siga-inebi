const API_URL = import.meta.env.VITE_API_URL || "/api/v1";

function getErrorMessage(detail) {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail.find((item) => typeof item === "string") || "Solicitud no completada.";
  }

  if (detail && typeof detail === "object") {
    const nested = detail.non_field_errors || detail.detail || Object.values(detail)[0];
    return getErrorMessage(nested);
  }

  return "Solicitud no completada.";
}

async function parseResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await response.json() : null;

  if (!response.ok) {
    const detail = data?.error?.detail || data?.detail || "Solicitud no completada.";
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

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const method = (options.method || "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) {
      headers.set("X-CSRFToken", csrfToken);
    }
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    method,
    credentials: "include",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  return parseResponse(response);
}

export const apiClient = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body }),
};
