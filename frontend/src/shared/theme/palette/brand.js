/**
 * brand.js — Interruptor de marca.
 *
 * Cambiar la identidad visual completa del sistema es cambiar `ACTIVE_BRAND`.
 * Nada mas. Los componentes nunca leen esta rampa: la consumen `light.js` y
 * `dark.js` para llenar el slot `primary` de MUI, y de ahi baja al resto de la
 * UI por tokens (`primary.main`, `softTone`, `selectedToneSx`).
 *
 * Decision de identidad de SIGA-INEBI: el primario NO es el mismo en los dos
 * modos. En claro manda el navy institucional sobre hueso; en oscuro manda el
 * DORADO sobre carbon calido. Un navy sobre fondo oscuro pierde casi todo el
 * contraste y hay que aclararlo tanto que termina siendo un celeste que ya no
 * es la marca; el dorado, en cambio, es exactamente el color del escudo y sobre
 * carbon rinde AA de sobra. La marca se conserva cambiando de portador, no
 * destinendo el mismo color.
 */

import { raw } from "./raw.js";

/** Rampas disponibles. Agregar una identidad nueva es agregar una entrada aqui. */
export const BRAND_RAMPS = {
  /** Navy + dorado del INEBI de Salcaja. */
  inebi: {
    light: {
      main: raw.navy400,
      light: raw.navy300,
      dark: raw.navy500,
      contrastText: raw.white,
    },
    dark: {
      main: raw.gold_d_main,
      light: raw.gold100,
      dark: raw.gold400,
      // Texto oscuro sobre boton dorado: el blanco sobre oro no llega a AA.
      contrastText: raw.navy500,
    },
    accent: { main: raw.gold400, dark: raw.gold_d_main },
    chip: {
      bg: raw.navy50,
      text: raw.navy400,
      bgDark: raw.chip_navy_bg_dark,
      textDark: raw.navy_d_main,
    },
  },
  /** Variante monocroma: tinta en claro, hueso en oscuro. Sin color de marca. */
  ink: {
    light: {
      main: raw.navy500,
      light: raw.navy300,
      dark: raw.black,
      contrastText: raw.white,
    },
    dark: {
      main: raw.dark_text_primary,
      light: raw.white,
      dark: raw.stone500,
      contrastText: raw.navy500,
    },
    accent: { main: raw.stone700, dark: raw.dark_text_secondary },
    chip: {
      bg: raw.bone200,
      text: raw.navy400,
      bgDark: raw.chip_stone_bg_dark,
      textDark: raw.dark_text_primary,
    },
  },
};

/** Marca activa. */
export const ACTIVE_BRAND = "inebi";

export const brand = BRAND_RAMPS[ACTIVE_BRAND];
