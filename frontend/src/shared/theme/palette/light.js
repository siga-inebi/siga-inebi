/**
 * light.js — Mapeo raw -> slots de MUI para el modo claro.
 *
 * Regla de la guia (seccion 4.3): `error`, `warning`, `success`, `info` y
 * `secondary` solo declaran `main`. MUI deriva `light` y `dark` solo; declarar
 * a mano lo que la libreria ya calcula bien es una fuente de deriva.
 */

import { brand } from "./brand.js";
import { raw } from "./raw.js";
import { variantsLight } from "../tokens/variants.js";

export const lightPalette = {
  mode: "light",
  primary: {
    main: brand.light.main,
    light: brand.light.light,
    dark: brand.light.dark,
    contrastText: raw.white,
  },
  secondary: { main: raw.green300 },
  success: { main: raw.green300 },
  error: { main: raw.red300 },
  warning: { main: raw.amber400 },
  info: { main: brand.light.main },
  background: {
    default: raw.gray100,
    paper: raw.white,
  },
  divider: raw.gray300,
  text: {
    primary: raw.gray900,
    secondary: raw.gray700,
    disabled: raw.gray500,
  },
  common: { white: raw.white, black: raw.black },
  /** Superficies que no son slots estandar de MUI pero se repiten en la UI. */
  surfaces: {
    tableHead: raw.gray150,
    inputBorder: raw.gray400,
    inputHoverBorder: raw.blue200,
    brandAccent: brand.accent.main,
  },
  /** Colores de chip de estado, resueltos por variante semantica. */
  chipVariants: variantsLight,
};
