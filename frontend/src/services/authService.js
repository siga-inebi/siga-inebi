import { apiClient } from "./apiClient";

export const authService = {
  csrf: () => apiClient.get("/auth/login/"),
  login: (credentials) => apiClient.post("/auth/login/", credentials),
  logout: () => apiClient.post("/auth/logout/", {}),
  me: () => apiClient.get("/auth/me/"),
};
