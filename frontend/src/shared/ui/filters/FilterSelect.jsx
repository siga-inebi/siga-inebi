import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";

/**
 * Select compacto para la barra de filtros de un listado.
 *
 * Es un `TextField select` y no un `Select` suelto porque asi hereda label
 * flotante, tamano y anillo de foco del tema sin configuracion extra.
 *
 * Los filtros que se alimentan de un catalogo del backend pasan `loading` y una
 * opcion vacia (`emptyLabel`, tipicamente "Todos"): sin la opcion vacia el
 * filtro no se puede quitar una vez elegido.
 *
 * @param {object} props
 * @param {string} props.label
 * @param {string} props.value
 * @param {Function} props.onChange   Recibe el valor ya desempaquetado.
 * @param {Array<{value:string,label:string}>} props.options
 * @param {string} [props.emptyLabel] Etiqueta de la opcion "sin filtro".
 * @param {boolean}[props.loading]
 * @param {number} [props.minWidth=140]
 */
export function FilterSelect({
  emptyLabel,
  loading = false,
  label,
  minWidth = 140,
  onChange,
  options,
  value,
}) {
  return (
    <TextField
      disabled={loading && options.length === 0}
      fullWidth={false}
      label={label}
      onChange={(event) => onChange(event.target.value)}
      select
      slotProps={{ inputLabel: { shrink: true } }}
      sx={{ minWidth }}
      value={value}
    >
      {emptyLabel ? <MenuItem value="">{emptyLabel}</MenuItem> : null}
      {loading && options.length === 0 ? (
        <MenuItem disabled value="">
          Cargando…
        </MenuItem>
      ) : null}
      {options.map((option) => (
        <MenuItem key={option.value} value={option.value}>
          {option.label}
        </MenuItem>
      ))}
    </TextField>
  );
}
