/**
 * light.js — Mapeo raw -> slots de MUI para el modo claro.
 *
 * Los slots semanticos (`error`, `warning`, `success`, `info`, `secondary`) solo
 * declaran `main`: MUI deriva `light` y `dark` solo, y declarar a mano lo que la
 * libreria ya calcula bien es una fuente de deriva entre pantallas.
 */

import { brand } from "./brand.js";
import { raw } from "./raw.js";
import { variantsLight } from "../tokens/variants.js";

export const lightPalette = {
  mode: "light",
  primary: brand.light,
  secondary: { main: raw.gold400 },
  success: { main: raw.green300 },
  error: { main: raw.red300 },
  warning: { main: raw.amber400 },
  info: { main: raw.navy300 },
  background: {
    default: raw.bone100,
    paper: raw.white,
  },
  divider: raw.bone300,
  text: {
    primary: raw.navy400,
    secondary: raw.stone700,
    disabled: raw.stone500,
  },
  common: { white: raw.white, black: raw.black },
  /** Superficies que no son slots estandar de MUI pero se repiten en la UI. */
  surfaces: {
    /** Cabecera de tabla: sin relleno. La jerarquia la da la regla inferior. */
    tableHead: "transparent",
    tableHeadRule: raw.navy400,
    inputBorder: raw.bone400,
    inputHoverBorder: raw.navy200,
    /** Marcador dorado del encabezado de seccion: la firma visual del sistema. */
    sectionMarker: raw.gold400,
    sunken: raw.bone200,
  },
  /** Colores de chip de estado, resueltos por variante semantica. */
  chipVariants: variantsLight,
};
