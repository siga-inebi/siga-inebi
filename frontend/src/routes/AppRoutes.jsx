import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { useAuth } from "../hooks/useAuth.js";
import { AppLayout } from "../layouts/AppLayout.jsx";
import { AlumnosPage } from "../pages/AlumnosPage.jsx";
import { CampusesPage } from "../pages/CampusesPage.jsx";
import { DashboardPage } from "../pages/DashboardPage.jsx";
import { DocentesPage } from "../pages/DocentesPage.jsx";
import { GuardiansPage } from "../pages/GuardiansPage.jsx";
import { HomePage } from "../pages/HomePage.jsx";
import { LevelsPage } from "../pages/LevelsPage.jsx";
import { LoginPage } from "../pages/LoginPage.jsx";
import { NotFoundPage } from "../pages/NotFoundPage.jsx";
import { PersonasPage } from "../pages/PersonasPage.jsx";
import { SubjectsPage } from "../pages/SubjectsPage.jsx";

function PrivateRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="panel">Cargando...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate replace state={{ from: location }} to="/login" />;
  }

  return children;
}

export function AppRoutes() {
  return (
    <AppLayout>
      <Routes>
        <Route element={<HomePage />} path="/" />
        <Route element={<LoginPage />} path="/login" />
        <Route
          element={
            <PrivateRoute>
              <DashboardPage />
            </PrivateRoute>
          }
          path="/app"
        />
        <Route
          element={
            <PrivateRoute>
              <PersonasPage />
            </PrivateRoute>
          }
          path="/app/personas"
        />
        <Route
          element={
            <PrivateRoute>
              <CampusesPage />
            </PrivateRoute>
          }
          path="/app/sedes"
        />
        <Route
          element={
            <PrivateRoute>
              <LevelsPage />
            </PrivateRoute>
          }
          path="/app/niveles"
        />
        <Route
          element={
            <PrivateRoute>
              <SubjectsPage />
            </PrivateRoute>
          }
          path="/app/cursos"
        />

        <Route element={<NotFoundPage />} path="*" />
      </Routes>
    </AppLayout>
  );
}
