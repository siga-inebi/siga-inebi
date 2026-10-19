import { useCallback, useRef } from "react";

import { apiClient } from "@shared/api/apiClient.js";

/** Como maximo una renovacion por minuto. */
export const KEEP_ALIVE_INTERVAL_MS = 60_000;

/**
 * Riesgo D (ADR-0011): escribir en un formulario con cambios sin guardar
 * cuenta como actividad.
 *
 * El servidor cierra la sesion por inactividad contando solo peticiones; quien
 * llena un formulario largo sin guardar no hace ninguna y podia perderlo. Este
 * hook devuelve `onActivity`, que se llama en cada tecla: si el formulario
 * esta sucio (`dirty`) y paso al menos un minuto desde la ultima renovacion,
 * envia `POST /auth/session/keep-alive/`. Mover el raton no cuenta: no es
 * trabajo sobre el formulario.
 *
 * @param {boolean} dirty
 * @param {{now?: () => number, send?: () => Promise<unknown>}} [options] Inyectables para pruebas.
 */
export function useSessionKeepAlive(dirty, options = {}) {
  const lastSentRef = useRef(0);
  const {
    now = Date.now,
    send = () => apiClient.post("/auth/session/keep-alive/", {}),
  } = options;

  return useCallback(() => {
    if (!dirty) return false;
    const current = now();
    if (current - lastSentRef.current < KEEP_ALIVE_INTERVAL_MS) return false;
    lastSentRef.current = current;
    send().catch(() => {
      // Si la sesion ya vencio, el aviso global de sesion se encarga.
    });
    return true;
  }, [dirty, now, send]);
}
