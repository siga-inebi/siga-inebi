/**
 * MuiForm.js — Defaults e inputs de formulario.
 *
 * `size: "small"` y `fullWidth: true` como defaults globales evitan que cada
 * formulario del sistema tenga que repetirlos; el anillo de foco de 3px es la
 * senal de accesibilidad principal de los inputs (la guia exige foco visible).
 */

import { alpha } from "@mui/material/styles";

import { appRadii } from "../tokens/radii.js";

export const MuiTextField = {
  defaultProps: { size: "small", fullWidth: true },
};

export const MuiFormControl = {
  defaultProps: { size: "small" },
};

export const MuiSelect = {
  defaultProps: { size: "small" },
};

export const MuiInputBase = {
  styleOverrides: {
    root: { fontSize: "0.875rem" },
  },
};

export const MuiOutlinedInput = {
  styleOverrides: {
    root: ({ theme }) => ({
      borderRadius: appRadii.input,
      "& .MuiOutlinedInput-notchedOutline": {
        borderColor: theme.palette.surfaces.inputBorder,
      },
      "&:hover .MuiOutlinedInput-notchedOutline": {
        borderColor: theme.palette.surfaces.inputHoverBorder,
      },
      "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
        borderWidth: "1.5px",
      },
      "&.Mui-focused": {
        boxShadow: `0 0 0 3px ${alpha(theme.palette.primary.main, 0.12)}`,
      },
    }),
  },
};

export const MuiInputLabel = {
  styleOverrides: {
    root: { fontSize: "0.875rem" },
  },
};

export const MuiFormHelperText = {
  styleOverrides: {
    root: { fontSize: "0.75rem", marginLeft: 2 },
  },
};

export const MuiFormControlLabel = {
  styleOverrides: {
    label: { fontSize: "0.875rem" },
  },
};
