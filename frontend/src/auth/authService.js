import { apiClient } from "@shared/api/apiClient.js";

export const authService = {
  csrf: () => apiClient.get("/auth/login/"),
  login: (credentials) => apiClient.post("/auth/login/", credentials),
  logout: () => apiClient.post("/auth/logout/", {}),
  logoutAll: () => apiClient.post("/auth/logout/all/", {}),
  me: () => apiClient.get("/auth/me/"),
  changePassword: (data) => apiClient.post("/auth/password/change/", data),
};
