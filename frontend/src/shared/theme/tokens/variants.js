/**
 * variants.js — Variantes semanticas de chip (unica fuente de color de chip).
 *
 * El dominio nunca conoce colores: conoce nombres de variante. Un mapa de
 * dominio (`shared/constants/chipMaps.js`) traduce `estado -> variante` y el
 * tema resuelve el par {bg, text} correcto para el modo activo.
 *
 * Agregar una variante son 3 pasos: hex en `palette/raw.js`, par en
 * `variantsLight` + `variantsDark`, y ya esta disponible en `<StatusChip>`.
 */

import { brand } from "../palette/brand.js";
import { raw } from "../palette/raw.js";

export const variantsLight = {
  primary: { bg: brand.chip.bg, text: brand.chip.text },
  success: { bg: raw.green50, text: raw.green400 },
  warning: { bg: raw.amber50, text: raw.amber400 },
  danger: { bg: raw.red50, text: raw.red300 },
  purple: { bg: raw.purple50, text: raw.purple300 },
  neutral: { bg: raw.gray200, text: raw.gray700 },
  accent: { bg: raw.gold50, text: raw.gold500 },
};

export const variantsDark = {
  primary: { bg: brand.chip.bgDark, text: brand.chip.textDark },
  success: { bg: raw.chip_green_bg_dark, text: raw.green_d_main },
  warning: { bg: raw.chip_amber_bg_dark, text: raw.amber_d_text },
  danger: { bg: raw.chip_red_bg_dark, text: raw.red_d_main },
  purple: { bg: raw.chip_purple_bg_dark, text: raw.purple_d_text },
  neutral: { bg: raw.chip_gray_bg_dark, text: raw.dark_text_secondary },
  accent: { bg: raw.chip_gold_bg_dark, text: raw.gold_d_main },
};

/** Nombres validos de variante, para validacion y para el ciclo de hash. */
export const CHIP_VARIANTS = Object.keys(variantsLight);
