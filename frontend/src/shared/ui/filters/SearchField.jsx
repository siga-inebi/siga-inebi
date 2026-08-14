import { useEffect, useState } from "react";

import IconButton from "@mui/material/IconButton";
import InputAdornment from "@mui/material/InputAdornment";
import TextField from "@mui/material/TextField";
import ClearIcon from "@mui/icons-material/Clear";
import SearchIcon from "@mui/icons-material/Search";
import { palette } from "@theme/tokens/color.js";

/** Retardo por defecto antes de propagar lo tecleado. */
const DEFAULT_DEBOUNCE_MS = 400;

/**
 * Buscador pill con debounce.
 *
 * Mantiene su propio estado de texto para que el input responda a cada tecla
 * mientras el consumidor solo recibe el valor estabilizado; sin eso, cada letra
 * dispararia un filtrado (o una peticion) y el campo se sentiria trabado.
 *
 * @param {object}  props
 * @param {string}  props.value            Valor controlado (ya estabilizado).
 * @param {Function}props.onChange         Recibe el valor con debounce aplicado.
 * @param {string} [props.placeholder="Buscar..."]
 * @param {number} [props.debounceMs=400]
 */
export function SearchField({
  debounceMs = DEFAULT_DEBOUNCE_MS,
  onChange,
  placeholder = "Buscar...",
  value,
  ...rest
}) {
  const [text, setText] = useState(value);

  // Resincroniza cuando el consumidor limpia el filtro desde fuera
  // (ej. boton "Limpiar" de la barra de filtros).
  useEffect(() => {
    setText(value);
  }, [value]);

  useEffect(() => {
    if (text === value) return undefined;
    const timer = setTimeout(() => onChange(text), debounceMs);
    return () => clearTimeout(timer);
  }, [debounceMs, onChange, text, value]);

  return (
    <TextField
      fullWidth={false}
      onChange={(event) => setText(event.target.value)}
      placeholder={placeholder}
      slotProps={{
        input: {
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon fontSize="small" sx={{ color: "text.disabled" }} />
            </InputAdornment>
          ),
          endAdornment: text ? (
            <InputAdornment position="end">
              <IconButton
                aria-label="Limpiar busqueda"
                edge="end"
                onClick={() => {
                  setText("");
                  onChange("");
                }}
                size="small"
              >
                <ClearIcon fontSize="small" />
              </IconButton>
            </InputAdornment>
          ) : null,
        },
      }}
      sx={(theme) => ({
        minWidth: "14rem",
        flex: 1,
        "& .MuiOutlinedInput-root": {
          borderRadius: theme.tokens.radii.input,
          // Fondo hundido en reposo y papel al enfocar: el campo "se levanta"
          // sin sombra, coherente con el resto del sistema. El anillo de foco lo
          // aporta el override global de OutlinedInput.
          bgcolor: palette(theme).surfaces.sunken,
          "&.Mui-focused": { bgcolor: "background.paper" },
        },
      })}
      value={text}
      {...rest}
    />
  );
}
