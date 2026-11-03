/**
 * Reglas de presentacion del vencimiento de sesion (docs/ux-ui.md L4).
 *
 * El backend cierra la sesion tras N minutos sin peticiones (el mayor de los
 * roles vigentes, `session_idle_timeout_minutes` de `/auth/me/`). El frontend
 * no decide cuando vence: solo cuenta desde la ultima respuesta del servidor
 * para avisar ANTES y no perder lo que la persona estaba llenando.
 */

/** Motivo por el que se cerro la sesion, para explicarlo en el login (L4). */
export const SESSION_NOTICE = Object.freeze({ EXPIRED: "expired" });

/** Cuanto antes del vencimiento aparece el aviso. */
export const SESSION_WARNING_MS = 2 * 60_000;

/** Cada cuanto se revisa el tiempo restante. */
export const SESSION_TICK_MS = 1_000;

/**
 * Milisegundos que le quedan a la sesion.
 *
 * @param {number} lastActivityAt  Marca de tiempo de la ultima respuesta del servidor.
 * @param {number} timeoutMinutes
 * @param {number} [now]
 */
export function remainingSessionMs(
  lastActivityAt,
  timeoutMinutes,
  now = Date.now()
) {
  return lastActivityAt + timeoutMinutes * 60_000 - now;
}

/** "1:05" */
export function formatCountdown(ms) {
  const totalSeconds = Math.max(0, Math.ceil(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = String(totalSeconds % 60).padStart(2, "0");
  return `${minutes}:${seconds}`;
}
