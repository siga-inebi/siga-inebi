import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";

/**
 * Select de formulario.
 *
 * Mientras el catalogo carga muestra una opcion deshabilitada "Cargando…" en
 * vez de un select vacio: un desplegable sin opciones se lee como "no hay
 * nada", que es una respuesta distinta a "todavia no llega".
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
  return (
    <TextField
      error={Boolean(error)}
      helperText={error ?? helperText}
      select
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
