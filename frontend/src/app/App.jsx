import { AppErrorBoundary } from "../components/AppErrorBoundary.jsx";
import { AppRoutes } from "../routes/AppRoutes.jsx";
import { AuthProvider } from "../features/auth/AuthContext.jsx";

export function App() {
  return (
    <AppErrorBoundary>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </AppErrorBoundary>
  );
}
