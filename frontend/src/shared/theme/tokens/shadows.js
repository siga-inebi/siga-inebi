/**
 * shadows.js — Elevacion por rol semantico.
 *
 * Estrategia de superficie de SIGA-INEBI: **las superficies asentadas no tienen
 * sombra.** Cards, secciones y paneles se separan del fondo con un borde
 * hairline y con espacio, no con elevacion. La sombra queda reservada para lo
 * que de verdad flota sobre el contenido: ventanas modales, menus y popovers.
 *
 * Por que: una pantalla de back-office tiene diez o quince bloques a la vez. Si
 * cada uno proyecta sombra, ninguno destaca y la interfaz se ve algodonosa. Con
 * sombra solo en lo flotante, cuando algo se eleva significa de verdad "esto
 * esta encima y te esta esperando".
 */

/** Superficies asentadas: sin elevacion, a proposito. */
const FLAT = "none";

export const appShadows = {
  card: FLAT,
  cardHover: FLAT,
  cardActive: FLAT,
  /** Ventana modal flotante: sombra amplia y difusa, centrada. */
  window: "0 24px 64px -12px rgba(15,27,38,0.35), 0 4px 12px rgba(15,27,38,0.12)",
  dialog: "0 24px 64px -12px rgba(15,27,38,0.35), 0 4px 12px rgba(15,27,38,0.12)",
  menu: "0 8px 24px -6px rgba(15,27,38,0.22)",
  popover: "0 8px 28px -8px rgba(15,27,38,0.24)",
};

/**
 * Elevaciones 1-3 de MUI remapeadas al mismo lenguaje, para que un
 * `<Paper elevation={2}>` suelto no reintroduzca sombras en superficies
 * asentadas por accidente.
 */
export const appElevations = {
  1: FLAT,
  2: FLAT,
  3: appShadows.menu,
};
