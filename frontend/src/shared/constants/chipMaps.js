/**
 * chipMaps.js — Traduccion `estado de dominio -> variante semantica`.
 *
 * Estos mapas NO contienen colores, solo nombres de variante: el tema resuelve
 * que verde o que rojo toca en cada modo. Asi, cambiar la marca o ajustar
 * contraste no obliga a tocar ni una regla de dominio.
 *
 * Un mapa entra aqui solo si el enum tiene 4+ valores usados en 3+ archivos.
 * Para un booleano, va inline en el call site:
 *   <StatusChip variant={row.activo ? "success" : "neutral"} />
 */

/** Estado de un registro de catalogo o de una persona. */
export const ACTIVE_VARIANT = {
  true: "success",
  false: "neutral",
};

/** Etiqueta visible del estado activo/inactivo. */
export const ACTIVE_LABEL = {
  true: "Activo",
  false: "Inactivo",
};

/** Vinculo institucional de una persona con el establecimiento. */
export const LINK_VARIANT = {
  student: "primary",
  teacher: "purple",
  guardian: "accent",
  staff: "neutral",
};
