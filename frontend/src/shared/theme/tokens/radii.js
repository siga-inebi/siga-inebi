/**
 * radii.js — Radio de borde por rol semantico.
 *
 * Lenguaje de forma de SIGA-INEBI: ANGULOS CASI RECTOS. Nada de capsulas.
 * Un boton pill y una card muy redondeada leen como app de consumo; un
 * rectangulo con 6px lee como documento institucional, que es lo que este
 * sistema emite (constancias, listados, actas).
 *
 * Uso: `theme.tokens.radii.card`, `theme.tokens.radii.button`, etc.
 */

export const appRadii = {
  button: "0.375rem", // 6px
  input: "0.375rem", // 6px
  chip: "0.25rem", // 4px
  card: "0.5rem", // 8px
  dialog: "0.625rem", // 10px
  menu: "0.375rem", // 6px
  tooltip: "0.25rem", // 4px
};
