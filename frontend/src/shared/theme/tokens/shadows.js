/**
 * shadows.js — Sombras nombradas por rol semantico.
 *
 * Patron "Flat 2.0" de la guia: la separacion entre superficies se logra con
 * una sombra difusa MAS un anillo hairline de 1px, no con bordes gruesos. El
 * anillo es lo que mantiene el borde visible en pantallas donde la sombra casi
 * no se percibe, sin que la UI se vea "encajonada".
 */

export const appShadows = {
  card: "0 1px 4px rgba(0,0,0,0.08), 0 0 0 1px rgba(0,0,0,0.05)",
  cardHover: "0 2px 8px rgba(0,0,0,0.09), 0 0 0 1px rgba(0,0,0,0.04)",
  cardActive: "0 4px 16px rgba(0,0,0,0.11), 0 0 0 1px rgba(0,0,0,0.06)",
  dialog: "0 20px 60px rgba(0,0,0,0.15), 0 0 0 1px rgba(0,0,0,0.04)",
  menu: "0 4px 20px rgba(0,0,0,0.10), 0 0 0 1px rgba(0,0,0,0.05)",
  popover: "0 4px 24px rgba(0,0,0,0.12), 0 0 0 1px rgba(0,0,0,0.04)",
  /** Sombra direccional para el panel lateral derecho. */
  drawerRight: "-12px 0 32px -8px rgba(0,0,0,0.28)",
};

/**
 * Elevaciones 1-3 de MUI remapeadas al mismo lenguaje visual, para que un
 * `<Paper elevation={2}>` suelto no rompa la coherencia del sistema.
 */
export const appElevations = {
  1: "0 1px 4px rgba(0,0,0,0.07), 0 0 0 1px rgba(0,0,0,0.04)",
  2: appShadows.cardHover,
  3: "0 4px 16px rgba(0,0,0,0.10), 0 0 0 1px rgba(0,0,0,0.04)",
};
