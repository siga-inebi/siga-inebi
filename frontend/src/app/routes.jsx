import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { useAuth } from "@auth/useAuth.js";
import { AppShell } from "@layout/AppShell.jsx";
import { PublicShell } from "@layout/PublicShell.jsx";
import { RouteFallback } from "@ui/feedback/RouteFallback.jsx";
import { NotFoundPage } from "@ui/feedback/NotFoundPage.jsx";

import { HOME_ITEM, NAV_GROUPS } from "./navigation.js";
import { useModuleCounts } from "./useModuleCounts.js";

/**
 * Cada pagina se carga bajo demanda. `load` es exactamente la misma funcion que
 * usa el prefetch del menu lateral (ver `navigation.js`), asi que el hover
 * calienta el chunk que la ruta va a pedir, no una copia distinta.
 *
 * El login NO es perezoso: es la primera pantalla de un usuario sin sesion, y
 * partirla en un chunk aparte solo agrega un viaje de red antes de poder
 * escribir la contrasena.
 */
const LoginPage = lazy(() =>
  import("@auth/LoginPage.jsx").then((m) => ({ default: m.LoginPage }))
);
const HomePage = lazy(() =>
  import("@dashboard/HomePage.jsx").then((m) => ({ default: m.HomePage }))
);

/** Convierte un modulo del registro en un componente perezoso. */
function lazyModule(item) {
  return lazy(() =>
    item.load().then((module) => {
      // Las paginas exportan un nombre, no un default: se resuelve la primera
      // exportacion que sea un componente para no repetir el nombre aqui.
      const component =
        module.default ?? Object.values(module).find((value) => typeof value === "function");
      return { default: component };
    })
  );
}

const MODULE_ROUTES = [HOME_ITEM, ...NAV_GROUPS.flatMap((group) => group.items)].map(
  (item) => ({ ...item, Component: lazyModule(item) })
);

function PrivateRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  // Mientras se resuelve la sesion no se puede decidir: redirigir aqui mandaria
  // al login a un usuario que si tiene sesion valida, en cada recarga.
  if (loading) return <RouteFallback />;

  if (!isAuthenticated) {
    return <Navigate replace state={{ from: location }} to="/login" />;
  }

  return children;
}

/** Shell privado con la sesion ya resuelta. */
function PrivateLayout({ children }) {
  const { isAuthenticated, logout, user } = useAuth();
  const counts = useModuleCounts(isAuthenticated);

  return (
    <AppShell counts={counts} onLogout={logout} user={user}>
      <Suspense fallback={<RouteFallback />}>{children}</Suspense>
    </AppShell>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route
        element={
          <PublicShell>
            <Suspense fallback={<RouteFallback />}>
              <HomePage />
            </Suspense>
          </PublicShell>
        }
        path="/"
      />
      <Route
        element={
          <Suspense fallback={<RouteFallback />}>
            <LoginPage />
          </Suspense>
        }
        path="/login"
      />

      {MODULE_ROUTES.map(({ Component, key, path }) => (
        <Route
          element={
            <PrivateRoute>
              <PrivateLayout>
                <Component />
              </PrivateLayout>
            </PrivateRoute>
          }
          key={key}
          path={path}
        />
      ))}

      <Route
        element={
          <PublicShell>
            <NotFoundPage />
          </PublicShell>
        }
        path="*"
      />
    </Routes>
  );
}
