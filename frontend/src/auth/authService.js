import { apiClient } from "@shared/api/apiClient.js";

export const authService = {
  csrf: () => apiClient.get("/auth/login/"),
  login: (credentials) => apiClient.post("/auth/login/", credentials),
  logout: () => apiClient.post("/auth/logout/", {}),
  logoutAll: () => apiClient.post("/auth/logout/all/", {}),
  me: () => apiClient.get("/auth/me/"),
  changePassword: (data) => apiClient.post("/auth/password/change/", data),
  /** L1: activacion publica con usuario, codigo y contraseña nueva. */
  activate: (data) => apiClient.post("/identity/accounts/activate/", data),
  /** L2: uso publico de un enlace de restablecimiento. */
  consumePasswordReset: (data) =>
    apiClient.post("/identity/password-resets/consume/", data),
  /** MC2: reglas reales de contraseña (publico). */
  passwordPolicy: () => apiClient.get("/identity/password-policy/"),
  /** MC1: datos, roles con alcances y sesiones de la cuenta propia. */
  myAccount: () => apiClient.get("/identity/me/account/"),
  mySchedule: () => apiClient.get("/identity/me/schedule/"),
};
