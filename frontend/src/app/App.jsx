import CssBaseline from "@mui/material/CssBaseline";
import { ThemeProvider } from "@mui/material/styles";

import { AuthProvider } from "@auth/AuthProvider.jsx";
import { AppErrorBoundary } from "@ui/feedback/AppErrorBoundary.jsx";
import { theme } from "@theme/theme.js";

import { AppRoutes } from "./routes.jsx";

/**
 * Raiz de composicion de la aplicacion.
 *
 * Orden de providers a proposito: el tema envuelve todo para que incluso la
 * pantalla de error de `AppErrorBoundary` se pinte con el sistema de diseno; si
 * el boundary quedara por fuera, un fallo temprano mostraria HTML sin estilo.
 *
 * `defaultMode="system"` respeta la preferencia del sistema operativo en la
 * primera visita; a partir de ahi manda lo que el usuario elija en la barra
 * superior (persistido por MUI en localStorage["mui-mode"]).
 */
export function App() {
  return (
    <ThemeProvider defaultMode="system" theme={theme}>
      <CssBaseline enableColorScheme />
      <AppErrorBoundary>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </AppErrorBoundary>
    </ThemeProvider>
  );
}
