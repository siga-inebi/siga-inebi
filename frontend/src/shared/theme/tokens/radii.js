/**
 * radii.js — Radio de borde por rol semantico.
 *
 * Uso: `theme.tokens.radii.card`, `theme.tokens.radii.button`, etc.
 * Ningun componente escribe un radio a mano salvo las excepciones documentadas
 * en la guia (pills de filtro y busqueda, que usan 999px para ser capsulas
 * perfectas independientemente del alto).
 */

export const appRadii = {
  button: "2rem", // pills
  input: "0.625rem", // 10px
  chip: "0.75rem", // 12px
  card: "0.75rem", // 12px
  dialog: "1rem", // 16px
  menu: "0.75rem", // 12px
  tooltip: "0.375rem", // 6px
  pill: "999px", // capsula (chips de filtro, buscador)
};
