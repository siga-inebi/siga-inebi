/**
 * dark.js — Mapeo raw -> slots de MUI para el modo oscuro.
 *
 * No es el modo claro invertido: las superficies son carbon CALIDO (espejo
 * nocturno del hueso) y el primario cambia de portador a dorado (ver
 * `brand.js`). Los tonos semanticos suben de luminosidad lo necesario para
 * mantener contraste AA sobre `background.paper`, no se aclaran "a ojo".
 */

import { brand } from "./brand.js";
import { raw } from "./raw.js";
import { variantsDark } from "../tokens/variants.js";

export const darkPalette = {
  mode: "dark",
  primary: brand.dark,
  secondary: { main: raw.gold_d_main },
  success: { main: raw.green_d_main },
  error: { main: raw.red_d_main },
  warning: { main: raw.amber_d_text },
  info: { main: raw.navy_d_main },
  background: {
    default: raw.dark_bg,
    paper: raw.dark_surface,
  },
  divider: raw.dark_divider,
  text: {
    primary: raw.dark_text_primary,
    secondary: raw.dark_text_secondary,
    disabled: raw.dark_text_disabled,
  },
  common: { white: raw.white, black: raw.black },
  surfaces: {
    tableHead: "transparent",
    tableHeadRule: raw.gold_d_main,
    inputBorder: raw.dark_border,
    inputHoverBorder: raw.gold400,
    sectionMarker: raw.gold_d_main,
    sunken: raw.dark_surface2,
  },
  chipVariants: variantsDark,
};
