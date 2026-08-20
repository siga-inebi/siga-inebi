import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";

import {
  MENU_MAX_HEIGHT,
  SEARCHABLE_FROM,
  SearchableSelect,
} from "./SearchableSelect.jsx";

/**
 * Select de formulario.
 *
 * Mientras el catalogo carga muestra una opcion deshabilitada "Cargando…" en
 * vez de un select vacio: un desplegable sin opciones se lee como "no hay
 * nada", que es una respuesta distinta a "todavia no llega".
 *
 * A partir de `SEARCHABLE_FROM` opciones delega en `SearchableSelect`. El
 * contrato de `onChange` es el de un input nativo (`event.target.value`) en las
 * dos variantes, para que las pantallas no tengan que saber cual les toco.
 *
 * @param {object}  props
 * @param {Array<{value:string|number,label:string}>} props.options
 * @param {boolean}[props.loading]
 * @param {string} [props.error]
 * @param {string} [props.placeholder] Opcion vacia inicial.
 */
export function FormSelect({
  error,
  helperText,
  loading = false,
  options,
  placeholder,
  ...rest
}) {
  // `||` y no `??`: un error vacio ("" es el estado "sin error" que usan
  // los catalogos) tiene que dejar pasar el texto de ayuda, y `??` solo
  // descarta null/undefined.
  const resolvedHelperText = error || helperText;

  if (!loading && options.length >= SEARCHABLE_FROM) {
    return (
      <SearchableSelect
        error={error}
        helperText={resolvedHelperText}
        options={options}
        placeholder={placeholder}
        {...rest}
      />
    );
  }

  return (
    <TextField
      error={Boolean(error)}
      helperText={resolvedHelperText}
      select
      slotProps={{
        select: {
          MenuProps: {
            slotProps: { paper: { sx: { maxHeight: MENU_MAX_HEIGHT } } },
          },
        },
      }}
      {...rest}
    >
      {placeholder ? (
        <MenuItem value="">
          <em>{placeholder}</em>
        </MenuItem>
      ) : null}
      {loading ? (
        <MenuItem disabled value="">
          Cargando…
        </MenuItem>
      ) : (
        options.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            {option.label}
          </MenuItem>
        ))
      )}
    </TextField>
  );
}
