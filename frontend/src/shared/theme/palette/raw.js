/**
 * raw.js — UNICO archivo del proyecto donde pueden existir literales de color.
 *
 * Regla dura (guia de diseno de Vantum ST, seccion 4.1): ningun componente,
 * pagina, hook o servicio puede escribir `#rrggbb` ni `rgb()/rgba()`. Si un
 * color hace falta en algun lado, primero entra aqui con nombre, despues se
 * mapea a un slot semantico en `light.js` / `dark.js` o a una variante de chip
 * en `tokens/variants.js`, y recien ahi lo consume la UI.
 *
 * Por que: mover el sistema entero de color (rebrand, cliente nuevo, ajuste de
 * contraste) tiene que ser editar un archivo, no perseguir hex por 60 archivos.
 */

export const raw = {
  // ── Azul de marca Vantum (Google Blue) ────────────────────────────────
  blue50: "#E8F0FE",
  blue100: "#D2E3FC",
  blue200: "#AECBFA",
  blue300: "#4285F4",
  blue400: "#1A73E8",
  blue500: "#1557B0",
  blue600: "#174EA6",
  blue700: "#1967D2",
  blue800: "#1D4ED8",
  blue_d_main: "#8AB4F8",
  blue_d_light: "#AECBFA",
  blue_d_dark: "#669DF6",

  // ── Marca INEBI (navy + dorado del establecimiento) ───────────────────
  // Se usan como rampa alterna de `primary` (ver `brand.js`) y para las
  // superficies de marca del login y del logotipo.
  navy50: "#EEF1F4",
  navy100: "#D7DDE4",
  navy200: "#9FAFBF",
  navy300: "#33475B",
  navy400: "#1C2B3A",
  navy500: "#0F1B26",
  navy_d_main: "#9FB6CC",
  navy_d_light: "#C6D4E1",
  navy_d_dark: "#7C97B2",

  gold50: "#FAF3E6",
  gold100: "#F0E1C4",
  gold300: "#C9A063",
  gold400: "#B4894A",
  gold500: "#8C6733",
  gold_d_main: "#DCBB84",

  // ── Verde ─────────────────────────────────────────────────────────────
  green50: "#E6F4EA",
  green100: "#CEEAD6",
  green200: "#D1FAE5",
  green300: "#34A853",
  green400: "#137333",
  green500: "#065F46",
  green_d_main: "#81C995",

  // ── Rojo ──────────────────────────────────────────────────────────────
  red50: "#FCE8E6",
  red100: "#FEE2E2",
  red200: "#FAD2CF",
  red300: "#C5221F",
  red400: "#A50E0E",
  red500: "#991B1B",
  red_d_main: "#F28B82",

  // ── Ambar ─────────────────────────────────────────────────────────────
  amber50: "#FEF0CD",
  amber100: "#FEF9C3",
  amber200: "#FFF3CD",
  amber300: "#FEF7E0",
  amber400: "#B06000",
  amber500: "#856404",
  amber600: "#854D0E",
  amber_d_text: "#FFB74D",

  // ── Morado ────────────────────────────────────────────────────────────
  purple50: "#EDE7F6",
  purple100: "#D1C4E9",
  purple300: "#5E35B1",
  purple400: "#512DA8",
  purple_d_text: "#CE93D8",

  // ── Neutrales ─────────────────────────────────────────────────────────
  white: "#FFFFFF",
  black: "#000000",
  gray50: "#F8F9FA",
  gray100: "#F4F6FB",
  gray150: "#F7F9FC",
  gray200: "#F1F3F4",
  gray300: "#E8EAED",
  gray400: "#DADCE0",
  gray500: "#9AA0A6",
  gray600: "#6B7280",
  gray700: "#5F6368",
  gray800: "#202124",
  gray900: "#1C2B3A",

  // ── Superficies modo oscuro ───────────────────────────────────────────
  dark_bg: "#1A1B1E",
  dark_surface: "#242628",
  dark_surface2: "#1F2023",
  dark_divider: "#3C4043",
  dark_border: "#5F6368",
  dark_text_primary: "#E3E4E8",
  dark_text_secondary: "#9AA0A6",
  dark_text_disabled: "#5F6368",

  // ── Fondos de chip en modo oscuro (todos al 20% de opacidad) ──────────
  chip_green_bg_dark: "rgba(52,168,83,0.20)",
  chip_blue_bg_dark: "rgba(26,115,232,0.20)",
  chip_red_bg_dark: "rgba(197,34,31,0.20)",
  chip_amber_bg_dark: "rgba(176,96,0,0.20)",
  chip_gray_bg_dark: "rgba(95,99,104,0.20)",
  chip_purple_bg_dark: "rgba(94,53,177,0.20)",
  chip_navy_bg_dark: "rgba(159,182,204,0.20)",
  chip_gold_bg_dark: "rgba(180,137,74,0.22)",
};
