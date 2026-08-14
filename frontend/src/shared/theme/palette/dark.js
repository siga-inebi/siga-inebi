/**
 * dark.js — Mapeo raw -> slots de MUI para el modo oscuro.
 *
 * Mismo contrato que `light.js`: solo `main` en los slots semanticos, el resto
 * lo deriva MUI. Los valores oscuros no son el mismo hex aclarado: son tonos
 * elegidos para mantener contraste AA sobre `background.paper` oscuro.
 */

import { brand } from "./brand.js";
import { raw } from "./raw.js";
import { variantsDark } from "../tokens/variants.js";

export const darkPalette = {
  mode: "dark",
  primary: {
    main: brand.dark.main,
    light: brand.dark.light,
    dark: brand.dark.dark,
    contrastText: raw.gray900,
  },
  secondary: { main: raw.green_d_main },
  success: { main: raw.green_d_main },
  error: { main: raw.red_d_main },
  warning: { main: raw.amber_d_text },
  info: { main: brand.dark.main },
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
    tableHead: raw.dark_surface2,
    inputBorder: raw.dark_border,
    inputHoverBorder: brand.dark.light,
    brandAccent: brand.accent.dark,
  },
  chipVariants: variantsDark,
};
