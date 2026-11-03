import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

import { authService } from "@auth/authService.js";
import {
  API_ACTIVITY_EVENT,
  MUTATION_EVENT,
  SESSION_EXPIRED_EVENT,
} from "@shared/api/apiClient.js";

import { AuthContext } from "./context.js";

// Solo se descarga cuando hay que avisar: no pesa en la primera pantalla.
const SessionTimeoutDialog = lazy(() =>
  import("./SessionTimeoutDialog.jsx").then((module) => ({
    default: module.SessionTimeoutDialog,
  }))
);
import {
  SESSION_NOTICE,
  SESSION_TICK_MS,
  SESSION_WARNING_MS,
  remainingSessionMs,
} from "./sessionTimer.js";

/**
 * Sesion de la aplicacion.
 *
 * Ademas de quien es la cuenta (`/auth/me/`, con sus permisos efectivos), lleva
 * la cuenta regresiva de inactividad: cada respuesta del servidor renueva la
 * sesion alla, asi que aqui se reinicia el reloj con el evento
 * `siga:api-activity`. Dos minutos antes del cierre se ofrece "Seguir
 * conectado"; si la sesion vence (aqui o en el servidor) la persona vuelve al
 * login con el mensaje "Su sesion se cerro por inactividad" y, al entrar, a la
 * misma pagina (`state.from`).
 */
export function AuthProvider({ children }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sessionNotice, setSessionNotice] = useState(null);
  const [remainingMs, setRemainingMs] = useState(null);
  const [extending, setExtending] = useState(false);
  const lastActivityRef = useRef(Date.now());

  const endSession = useCallback(
    (notice = null) => {
      setUser(null);
      setRemainingMs(null);
      setSessionNotice(notice);
      // Nada de lo cacheado para una cuenta debe verlo la siguiente.
      queryClient.clear();
    },
    [queryClient]
  );

  useEffect(() => {
    let active = true;
    authService
      .me()
      .then((session) => {
        if (active) {
          setUser(session?.authenticated ? session.user : null);
          lastActivityRef.current = Date.now();
        }
      })
      .catch(() => {
        if (active) {
          setUser(null);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const handleSessionExpired = () => endSession(SESSION_NOTICE.EXPIRED);
    const handleActivity = () => {
      lastActivityRef.current = Date.now();
    };
    // Editar un rol propio o sus asignaciones cambia los permisos efectivos:
    // se vuelve a leer `/auth/me/` para que el menu refleje el cambio.
    const handleMutation = (event) => {
      const path = event.detail?.path ?? "";
      if (
        path.startsWith("/identity/roles") ||
        path.startsWith("/identity/role-assignments")
      ) {
        authService
          .me()
          .then((session) => {
            if (session?.authenticated) setUser(session.user);
          })
          .catch(() => {});
      }
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
    window.addEventListener(API_ACTIVITY_EVENT, handleActivity);
    window.addEventListener(MUTATION_EVENT, handleMutation);
    return () => {
      window.removeEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
      window.removeEventListener(API_ACTIVITY_EVENT, handleActivity);
      window.removeEventListener(MUTATION_EVENT, handleMutation);
    };
  }, [endSession]);

  const timeoutMinutes = user?.session_idle_timeout_minutes;

  useEffect(() => {
    if (!user || !timeoutMinutes) return undefined;
    const tick = () => {
      const remaining = remainingSessionMs(
        lastActivityRef.current,
        timeoutMinutes
      );
      if (remaining <= 0) {
        // El servidor ya la cerro (o la cerrara en la proxima peticion): se
        // limpia la sesion local sin esperar a que una peticion lo descubra.
        authService.logout().catch(() => {});
        endSession(SESSION_NOTICE.EXPIRED);
        return;
      }
      setRemainingMs(remaining <= SESSION_WARNING_MS ? remaining : null);
    };
    tick();
    const interval = window.setInterval(tick, SESSION_TICK_MS);
    return () => window.clearInterval(interval);
  }, [user, timeoutMinutes, endSession]);

  const login = async (credentials) => {
    await authService.csrf();
    const currentUser = await authService.login(credentials);
    // La respuesta del login trae la cuenta; los permisos y el tiempo de
    // inactividad vienen de `/auth/me/`.
    let sessionUser = currentUser;
    try {
      const session = await authService.me();
      if (session?.authenticated) sessionUser = session.user;
    } catch {
      // Si `me` falla se conserva lo que devolvio el login.
    }
    lastActivityRef.current = Date.now();
    setSessionNotice(null);
    setUser(sessionUser);
    return sessionUser;
  };

  const logout = async () => {
    await authService.logout();
    endSession();
  };

  const logoutAll = async () => {
    await authService.logoutAll();
    endSession();
  };

  const stayConnected = async () => {
    setExtending(true);
    try {
      // Cualquier peticion autenticada renueva la sesion en el servidor.
      const session = await authService.me();
      if (session?.authenticated) {
        lastActivityRef.current = Date.now();
        setUser(session.user);
        setRemainingMs(null);
      } else {
        endSession(SESSION_NOTICE.EXPIRED);
      }
    } catch {
      // Un 401 por sesion vencida ya disparo `siga:session-expired`.
    } finally {
      setExtending(false);
    }
  };

  const refreshUser = async () => {
    const session = await authService.me();
    setUser(session?.authenticated ? session.user : null);
    return session?.user ?? null;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: Boolean(user),
        login,
        logout,
        logoutAll,
        refreshUser,
        sessionNotice,
        clearSessionNotice: () => setSessionNotice(null),
      }}
    >
      {children}
      {user && remainingMs !== null ? (
        <Suspense fallback={null}>
          <SessionTimeoutDialog
            busy={extending}
            onLogout={logout}
            onStay={stayConnected}
            open
            remainingMs={remainingMs}
          />
        </Suspense>
      ) : null}
    </AuthContext.Provider>
  );
}
