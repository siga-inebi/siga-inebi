import { AppRoutes } from "../routes/AppRoutes";
import { AuthProvider } from "../features/auth/AuthContext";

export function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
