/**
 * brand.js — Interruptor de marca.
 *
 * Cambiar la identidad visual completa del sistema es cambiar `ACTIVE_BRAND`.
 * Nada mas. Los componentes nunca leen esta rampa directamente: la consumen
 * `light.js` y `dark.js` para llenar el slot `primary` de MUI, y de ahi baja al
 * resto de la UI por tokens (`primary.main`, `softTone`, `selectedToneSx`).
 *
 * Por que existe: la guia de diseno de Vantum ST fija el azul corporativo como
 * primario para que todos los productos de la casa se sientan iguales, pero
 * SIGA-INEBI tiene marca propia (navy + dorado del establecimiento). En vez de
 * elegir de una vez y regarlo por el codigo, la decision queda aislada en una
 * constante para poder probar ambas sin tocar un solo componente.
 */

import { raw } from "./raw.js";

/** Rampas disponibles. Agregar una marca nueva es agregar una entrada aqui. */
export const BRAND_RAMPS = {
  /** Azul corporativo Vantum ST — default de la guia de diseno de empresa. */
  vantum: {
    light: { main: raw.blue400, light: raw.blue300, dark: raw.blue500 },
    dark: { main: raw.blue_d_main, light: raw.blue_d_light, dark: raw.blue_d_dark },
    accent: { main: raw.gold400, dark: raw.gold_d_main },
    chip: { bg: raw.blue50, text: raw.blue400, bgDark: raw.chip_blue_bg_dark, textDark: raw.blue_d_main },
  },
  /** Navy + dorado del INEBI de Salcaja. */
  inebi: {
    light: { main: raw.navy400, light: raw.navy300, dark: raw.navy500 },
    dark: { main: raw.navy_d_main, light: raw.navy_d_light, dark: raw.navy_d_dark },
    accent: { main: raw.gold400, dark: raw.gold_d_main },
    chip: { bg: raw.navy50, text: raw.navy400, bgDark: raw.chip_navy_bg_dark, textDark: raw.navy_d_main },
  },
};

/**
 * Marca activa. Cambiar a "inebi" repinta botones, enlaces, foco, estados
 * seleccionados y el chip primario en ambos modos.
 */
export const ACTIVE_BRAND = "vantum";

export const brand = BRAND_RAMPS[ACTIVE_BRAND];
