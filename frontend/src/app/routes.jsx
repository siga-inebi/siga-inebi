import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { useAuth } from "@auth/useAuth.js";
import { AppShell } from "@layout/AppShell.jsx";
import { PublicShell } from "@layout/PublicShell.jsx";
import { RouteFallback } from "@ui/feedback/RouteFallback.jsx";
import { NotFoundPage } from "@ui/feedback/NotFoundPage.jsx";

import {
  EXTRA_ROUTES,
  HOME_ITEM,
  NAV_GROUPS,
  canViewModule,
} from "./navigation.js";
import { useModuleCounts } from "./useModuleCounts.js";

/**
 * Cada pagina se carga bajo demanda. `load` es exactamente la misma funcion que
 * usa el prefetch del menu lateral (ver `navigation.js`), asi que el hover
 * calienta el chunk que la ruta va a pedir, no una copia distinta.
 */
const LoginPage = lazy(() =>
  import("@auth/LoginPage.jsx").then((m) => ({ default: m.LoginPage }))
);
const ActivationPage = lazy(() =>
  import("@auth/ActivationPage.jsx").then((m) => ({
    default: m.ActivationPage,
  }))
);
const PasswordResetPage = lazy(() =>
  import("@auth/PasswordResetPage.jsx").then((m) => ({
    default: m.PasswordResetPage,
  }))
);
const ForbiddenPage = lazy(() =>
  import("@ui/feedback/ForbiddenPage.jsx").then((m) => ({
    default: m.ForbiddenPage,
  }))
);
const StudentRecordPage = lazy(() =>
  import("@students/StudentRecordPage.jsx").then((module) => ({
    default: module.StudentRecordPage,
  }))
);

/** Convierte un modulo del registro en un componente perezoso. */
function lazyModule(item) {
  return lazy(() =>
    item.load().then((module) => {
      // Las paginas exportan un nombre, no un default: se resuelve la primera
      // exportacion que sea un componente para no repetir el nombre aqui.
      const component =
        module.default ??
        Object.values(module).find((value) => typeof value === "function");
      return { default: component };
    })
  );
}

const MODULE_ROUTES = [
  HOME_ITEM,
  ...NAV_GROUPS.flatMap((group) => group.items),
  ...EXTRA_ROUTES,
].map((item) => ({ ...item, Component: lazyModule(item) }));

function PrivateRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  // Mientras se resuelve la sesion no se puede decidir: redirigir aqui mandaria
  // al login a un usuario que si tiene sesion valida, en cada recarga.
  if (loading) return <RouteFallback />;

  if (!isAuthenticated) {
    // `from` permite volver a la misma pagina al entrar de nuevo (L4).
    return <Navigate replace state={{ from: location }} to="/login" />;
  }

  return children;
}

/**
 * Ruta de un modulo con permiso: sin el permiso se explica "sin acceso" en vez
 * de montar la pantalla y dejar que cada peticion responda 403 (ux-ui 1.4).
 */
function ModuleGate({ children, item }) {
  const { user } = useAuth();
  if (!canViewModule(user, item)) {
    return <ForbiddenPage moduleLabel={item.label} />;
  }
  return children;
}

/** Shell privado con la sesion ya resuelta. */
function PrivateLayout({ children }) {
  const { isAuthenticated, logout, logoutAll, user } = useAuth();
  const counts = useModuleCounts(isAuthenticated, user);

  return (
    <AppShell
      counts={counts}
      onLogout={logout}
      onLogoutAll={logoutAll}
      user={user}
    >
      <Suspense fallback={<RouteFallback />}>{children}</Suspense>
    </AppShell>
  );
}

function PublicRoute({ children }) {
  return <Suspense fallback={<RouteFallback />}>{children}</Suspense>;
}

/**
 * `/` no es una portada de marketing: SIGA es una herramienta institucional.
 * La raiz lleva a la siguiente accion util segun la sesion, sin mostrar una
 * pantalla intermedia que obligue a hacer otro clic.
 */
function RootRedirect() {
  const { isAuthenticated, loading } = useAuth();
  if (loading) return <RouteFallback />;
  return <Navigate replace to={isAuthenticated ? "/app" : "/login"} />;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/app/alumnos/:studentId"
        element={
          <PrivateRoute>
            <PrivateLayout>
              <StudentRecordPage />
            </PrivateLayout>
          </PrivateRoute>
        }
      />
      <Route element={<RootRedirect />} path="/" />
      <Route
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
        path="/login"
      />
      {/* L1 y L2: paginas publicas para activar la cuenta y usar un restablecimiento. */}
      <Route
        element={
          <PublicRoute>
            <ActivationPage />
          </PublicRoute>
        }
        path="/activar"
      />
      <Route
        element={
          <PublicRoute>
            <PasswordResetPage />
          </PublicRoute>
        }
        path="/restablecer"
      />

      {MODULE_ROUTES.map((item) => {
        const { Component, key, path } = item;
        return (
          <Route
            element={
              <PrivateRoute>
                <PrivateLayout>
                  <ModuleGate item={item}>
                    <Component />
                  </ModuleGate>
                </PrivateLayout>
              </PrivateRoute>
            }
            key={key}
            path={path}
          />
        );
      })}

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
