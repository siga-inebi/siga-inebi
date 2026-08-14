/**
 * fillHeight.js — Umbral del modo "un solo scroll por pantalla".
 *
 * El patron `fillHeight` reparte el alto del shell hasta la tabla, que scrollea
 * internamente con header pegado y paginacion anclada abajo. Eso elimina el
 * doble scroll (pagina + tabla), que es el defecto tipico de un back-office.
 *
 * Debajo de 640px de ALTO de viewport el patron se apaga por CSS: en pantallas
 * bajas (o con el teclado virtual abierto) forzar la tabla a llenar el alto deja
 * dos o tres filas visibles y una paginacion pegada al borde, que es peor que el
 * scroll normal de pagina.
 */

export const FILL_HEIGHT_MIN_VIEWPORT_PX = 640;

export const FILL_HEIGHT_QUERY = `@media (min-height: ${FILL_HEIGHT_MIN_VIEWPORT_PX}px)`;

/** Alto maximo de la tabla cuando el modo fillHeight esta apagado. */
export const TABLE_FALLBACK_MAX_HEIGHT = "min(70vh, 720px)";
