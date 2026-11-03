/**
 * typography.js — Las dos familias del sistema y sus roles.
 *
 * Cambiar la voz tipografica de toda la aplicacion es cambiar estas dos
 * constantes (y el `<link>` de fuentes en `index.html`).
 *
 * Reparto de roles, sin excepciones:
 *   DISPLAY (serif) -> titulos de pagina, titulos de seccion, numeros de
 *                      indicador. Textos cortos que se leen de un vistazo.
 *   BODY (sans)     -> absolutamente todo lo demas: celdas de tabla, campos,
 *                      etiquetas, botones, menus, chips.
 *
 * Ningun componente declara `fontFamily` por su cuenta: o hereda el sans, o
 * pide el serif con `theme.tokens.fonts.display`.
 */

/** Serif de titulos. */
export const DISPLAY_FONT = "Source Serif 4";

/** Sans de interfaz. */
export const BODY_FONT = "Public Sans";

export const DISPLAY_STACK = `"${DISPLAY_FONT}", Georgia, "Times New Roman", serif`;

export const BODY_STACK = `"${BODY_FONT}", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;

/** Monoespaciada para codigos e identificadores tecnicos. */
export const MONO_STACK = `"IBM Plex Mono", ui-monospace, SFMono-Regular, Menlo, monospace`;

export const appFonts = {
  display: DISPLAY_STACK,
  body: BODY_STACK,
  mono: MONO_STACK,
};
