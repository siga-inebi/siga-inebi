import MenuItem from "@mui/material/MenuItem";
import TextField from "@mui/material/TextField";

import {
  MENU_MAX_HEIGHT,
  SEARCHABLE_FROM,
  SearchableSelect,
} from "@ui/forms/SearchableSelect.jsx";

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
 * A partir de `SEARCHABLE_FROM` opciones se vuelve buscable, igual que
 * `FormSelect`. Filtrar por estudiante es el caso que lo pedia a gritos: el
 * historial de matricula se consulta por persona, y encontrarla entre cientos
 * bajando con la rueda del raton no es buscar. Ahi la opcion vacia deja de ser
 * una fila del menu y pasa a ser la "x" de limpiar, que es como se quita un
 * filtro en un buscador.
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
  if (!loading && options.length >= SEARCHABLE_FROM) {
    return (
      <SearchableSelect
        clearText={emptyLabel}
        label={label}
        onChange={(event) => onChange(event.target.value)}
        options={options}
        placeholder={emptyLabel}
        sx={{ minWidth }}
        value={value}
      />
    );
  }

  return (
    <TextField
      disabled={loading && options.length === 0}
      fullWidth={false}
      label={label}
      onChange={(event) => onChange(event.target.value)}
      select
      slotProps={{
        inputLabel: { shrink: true },
        select: {
          MenuProps: {
            slotProps: { paper: { sx: { maxHeight: MENU_MAX_HEIGHT } } },
          },
        },
      }}
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
