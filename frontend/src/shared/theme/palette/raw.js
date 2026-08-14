/**
 * raw.js — UNICO archivo del proyecto donde pueden existir literales de color.
 *
 * Regla dura: ningun componente, pagina, hook o servicio puede escribir
 * `#rrggbb` ni `rgb()/rgba()`. Si un color hace falta en algun lado, primero
 * entra aqui con nombre, despues se mapea a un slot semantico en `light.js` /
 * `dark.js` o a una variante de chip en `tokens/variants.js`, y recien ahi lo
 * consume la UI. La regla la aplica ESLint como error.
 *
 * Por que: mover el sistema entero de color (rebrand, ajuste de contraste, modo
 * oscuro) tiene que ser editar un archivo, no perseguir hex por 60 archivos.
 *
 * Identidad de SIGA-INEBI: navy y dorado del establecimiento sobre neutrales
 * CALIDOS (hueso, no gris azulado). Los neutrales tibios son la mitad de la
 * razon por la que el sistema no se siente como un panel corporativo generico:
 * un gris frio lee como software, un hueso lee como papel institucional.
 */

export const raw = {
  // ── Navy institucional (primario) ─────────────────────────────────────
  navy50: "#EAEDF1",
  navy100: "#D3DAE2",
  navy200: "#9BAAB9",
  navy300: "#33475B",
  navy400: "#1C2B3A",
  navy500: "#0F1B26",
  navy_d_main: "#A7BACD",
  navy_d_light: "#CBD8E4",
  navy_d_dark: "#849BB4",

  // ── Dorado institucional (acento de marca) ────────────────────────────
  gold50: "#F7EFE0",
  gold100: "#EBDABB",
  gold300: "#C9A063",
  gold400: "#B4894A",
  gold500: "#8C6733",
  gold_d_main: "#D9BA85",

  // ── Neutrales calidos (hueso / piedra) ───────────────────────────────
  white: "#FFFFFF",
  black: "#000000",
  bone50: "#FDFCFA",
  bone100: "#FAF8F4", // background.default (claro)
  bone200: "#F2EFE8", // hover / superficie hundida
  bone300: "#E6E1D6", // divider
  bone400: "#D5CEC0", // borde de input
  stone500: "#8C8578", // text.disabled
  stone600: "#6E675C",
  stone700: "#57514A", // text.secondary

  // ── Verde (activo, completado) ────────────────────────────────────────
  green50: "#E4F0E8",
  green300: "#1F7A4C",
  green400: "#1B6B43",
  green_d_main: "#7FC79E",

  // ── Rojo (baja, error) ────────────────────────────────────────────────
  red50: "#F8E7E5",
  red300: "#B3261E",
  red400: "#A11F17",
  red_d_main: "#F0B0AB",

  // ── Ambar (pendiente, suspendido) ─────────────────────────────────────
  amber50: "#F7EDD9",
  amber400: "#9A6700",
  amber500: "#8A5C00",
  amber_d_text: "#E8B14C",

  // ── Morado (roles especiales) ─────────────────────────────────────────
  purple50: "#EDE9F5",
  purple300: "#4E3F7A",
  purple_d_text: "#C4B5E0",

  // ── Superficies del modo oscuro ───────────────────────────────────────
  // Carbon CALIDO, no gris azulado: es el espejo nocturno del hueso del modo
  // claro. Un oscuro frio sobre una marca navy+oro se ve destenido; el tibio
  // deja que el dorado se lea como dorado y no como amarillo mostaza.
  dark_bg: "#191714",
  dark_surface: "#221F1B",
  dark_surface2: "#1D1A17",
  dark_divider: "#3B362F",
  dark_border: "#5A5348",
  dark_text_primary: "#EFEAE1",
  dark_text_secondary: "#ABA398",
  dark_text_disabled: "#6F6759",

  // ── Fondos de chip en modo oscuro (semitransparentes) ────────────────
  chip_navy_bg_dark: "rgba(167,186,205,0.18)",
  chip_gold_bg_dark: "rgba(180,137,74,0.22)",
  chip_green_bg_dark: "rgba(31,122,76,0.26)",
  chip_red_bg_dark: "rgba(179,38,30,0.26)",
  chip_amber_bg_dark: "rgba(154,103,0,0.28)",
  chip_purple_bg_dark: "rgba(78,63,122,0.30)",
  chip_stone_bg_dark: "rgba(87,81,74,0.35)",
};
