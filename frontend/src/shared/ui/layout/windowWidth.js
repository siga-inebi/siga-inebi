/**
 * windowWidth.js — Anchos estandarizados de la ventana modal.
 *
 * Vive aparte de `FloatingWindow.jsx` para no romper el fast refresh: un archivo
 * que exporta un componente y una constante deja de recargar en caliente y
 * obliga a refrescar el navegador en cada edicion.
 *
 * Fuera de estos tres anchos, justificar en el call site.
 */

export const WINDOW_WIDTH = {
  /** Formularios de 1 a 4 campos y confirmaciones. */
  compact: 520,
  /** Formularios de dominio y detalle de entidad: el default. */
  medium: 680,
  /** Tablas dentro de la ventana (historiales, expedientes, catalogos). */
  wide: 880,
};
