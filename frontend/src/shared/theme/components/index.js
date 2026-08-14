/**
 * index.js — Ensamble de todos los `styleOverrides` y `defaultProps`.
 *
 * Un solo objeto `components` para `createTheme()`. Los archivos vecinos
 * agrupan por familia (botones, formularios, tablas, superficies) para que
 * ajustar un componente no obligue a leer un archivo de 400 lineas.
 */

import { MuiButton, MuiIconButton, MuiToggleButton } from "./MuiButton.js";
import {
  MuiFormControl,
  MuiFormControlLabel,
  MuiFormHelperText,
  MuiInputBase,
  MuiInputLabel,
  MuiOutlinedInput,
  MuiSelect,
  MuiTextField,
} from "./MuiForm.js";
import {
  MuiCard,
  MuiChip,
  MuiDialog,
  MuiDialogTitle,
  MuiDivider,
  MuiDrawer,
  MuiLink,
  MuiMenu,
  MuiMenuItem,
  MuiPaper,
  MuiPopover,
  MuiSkeleton,
  MuiTooltip,
} from "./MuiSurfaces.js";
import { MuiTableCell, MuiTablePagination, MuiTableRow } from "./MuiTable.js";

export const appComponents = {
  MuiButton,
  MuiIconButton,
  MuiToggleButton,
  MuiTextField,
  MuiFormControl,
  MuiSelect,
  MuiInputBase,
  MuiOutlinedInput,
  MuiInputLabel,
  MuiFormHelperText,
  MuiFormControlLabel,
  MuiTableCell,
  MuiTableRow,
  MuiTablePagination,
  MuiPaper,
  MuiCard,
  MuiDialog,
  MuiDialogTitle,
  MuiDrawer,
  MuiMenu,
  MuiMenuItem,
  MuiPopover,
  MuiTooltip,
  MuiChip,
  MuiDivider,
  MuiSkeleton,
  MuiLink,
};
